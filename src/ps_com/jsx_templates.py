"""
Photoshop COM (`app.DoJavaScript`) に流し込む ExtendScript (ES3) テンプレート群。
PyInstallerで単一EXE化した際に外部ファイル参照エラーが起きないよう、Python定数として保持します。
"""

# ---------------------------------------------------------------------------
# 1. PSD/ドキュメント内部のレイヤー構造・画像メタデータ一括解析スクリプト
# ---------------------------------------------------------------------------
JSX_INSPECT_DOCUMENT = r"""
(function() {
    if (app.documents.length === 0) {
        return '{"error": "Photoshopで開かれているドキュメントがありません。"}';
    }
    var doc = app.activeDocument;
    var origRuler = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;

    function escapeJsonStr(s) {
        if (s === null || s === undefined) return "";
        return String(s)
            .replace(/\\/g, "\\\\")
            .replace(/"/g, '\\"')
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n");
    }

    var layersJson = [];
    var includeHidden = __INCLUDE_HIDDEN__;

    function traverse(container, parentPath, depth) {
        for (var i = 0; i < container.layers.length; i++) {
            var lyr = container.layers[i];
            if (!includeHidden && !lyr.visible) {
                continue;
            }
            var currentPath = parentPath ? (parentPath + "/" + lyr.name) : lyr.name;
            var b = lyr.bounds; // [left, top, right, bottom]
            var left = Math.round(b[0].as("px"));
            var top = Math.round(b[1].as("px"));
            var right = Math.round(b[2].as("px"));
            var bottom = Math.round(b[3].as("px"));
            var width = right - left;
            var height = bottom - top;

            var isGroup = (lyr.typename === "LayerSet");
            var kindStr = isGroup ? "GROUP" : String(lyr.kind);
            var textContent = "";
            if (!isGroup && lyr.kind === LayerKind.TEXT) {
                try { textContent = lyr.textItem.contents; } catch(e) {}
            }

            var itemJson = '{' +
                '"id": ' + lyr.id + ',' +
                '"name": "' + escapeJsonStr(lyr.name) + '",' +
                '"path": "' + escapeJsonStr(currentPath) + '",' +
                '"visible": ' + (lyr.visible ? 'true' : 'false') + ',' +
                '"opacity": ' + Math.round(lyr.opacity) + ',' +
                '"kind": "' + escapeJsonStr(kindStr) + '",' +
                '"x": ' + left + ',' +
                '"y": ' + top + ',' +
                '"width": ' + width + ',' +
                '"height": ' + height + ',' +
                '"text": "' + escapeJsonStr(textContent) + '"' +
            '}';
            layersJson.push(itemJson);

            if (isGroup && depth < 10) {
                traverse(lyr, currentPath, depth + 1);
            }
        }
    }

    try {
        var docPath = "";
        try { docPath = doc.fullName.fsName; } catch(e) { docPath = "(未保存ドキュメント)"; }
        traverse(doc, "", 0);
        app.preferences.rulerUnits = origRuler;
        return '{' +
            '"document_name": "' + escapeJsonStr(doc.name) + '",' +
            '"document_path": "' + escapeJsonStr(docPath) + '",' +
            '"width": ' + Math.round(doc.width.as("px")) + ',' +
            '"height": ' + Math.round(doc.height.as("px")) + ',' +
            '"resolution": ' + Math.round(doc.resolution) + ',' +
            '"layer_count": ' + layersJson.length + ',' +
            '"layers": [' + layersJson.join(",") + ']' +
        '}';
    } catch (err) {
        app.preferences.rulerUnits = origRuler;
        return '{"error": "' + escapeJsonStr(err.toString()) + '"}';
    }
})();
"""

# ---------------------------------------------------------------------------
# 2. 指定レイヤー（名前部分一致 または レイヤーID）の個別画像切り出し・書き出しスクリプト
# ---------------------------------------------------------------------------
JSX_EXPORT_MATCHING_LAYERS = r"""
(function() {
    if (app.documents.length === 0) {
        return '{"error": "Photoshopで開かれているドキュメントがありません。"}';
    }
    var srcDoc = app.activeDocument;
    var origRuler = app.preferences.rulerUnits;
    var origDialogs = app.displayDialogs;
    app.preferences.rulerUnits = Units.PIXELS;
    app.displayDialogs = DialogModes.NO;

    var targetQuery = "__TARGET_QUERY__";
    var outputDirStr = "__OUTPUT_DIR__";
    var formatStr = "__FORMAT__".toUpperCase(); // PNG or JPG
    var trimBounds = __TRIM_BOUNDS__;
    var onlyVisible = __ONLY_VISIBLE__;

    function escapeJsonStr(s) {
        if (s === null || s === undefined) return "";
        return String(s)
            .replace(/\\/g, "\\\\")
            .replace(/"/g, '\\"')
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n");
    }

    function sanitizeFileName(name) {
        return name.replace(/[\\\/:\*\?"<>\|]/g, "_");
    }

    var outFolder = new Folder(outputDirStr);
    if (!outFolder.exists) {
        outFolder.create();
    }

    var matchedLayers = [];
    function collectTargets(container) {
        for (var i = 0; i < container.layers.length; i++) {
            var lyr = container.layers[i];
            if (onlyVisible && !lyr.visible) continue;

            var nameMatched = (targetQuery === "*" || targetQuery === "" || lyr.name.indexOf(targetQuery) !== -1 || String(lyr.id) === targetQuery);
            if (nameMatched && lyr.typename !== "LayerSet") {
                matchedLayers.push(lyr);
            }
            if (lyr.typename === "LayerSet") {
                // グループ名自体がマッチし、かつグループ書き出ししたい場合にも対応できるよう走査
                if (nameMatched && targetQuery !== "*" && targetQuery !== "") {
                    matchedLayers.push(lyr);
                } else {
                    collectTargets(lyr);
                }
            }
        }
    }

    try {
        collectTargets(srcDoc);
        var exportedFiles = [];

        for (var j = 0; j < matchedLayers.length; j++) {
            var targetLayer = matchedLayers[j];
            var b = targetLayer.bounds;
            var w = Math.round(b[2].as("px") - b[0].as("px"));
            var h = Math.round(b[3].as("px") - b[1].as("px"));
            if (w <= 0 || h <= 0) continue; // 空レイヤーはスキップ

            // 対象レイヤーを新規一時ドキュメントへ複製して高速書き出し
            var tempDoc = app.documents.add(srcDoc.width, srcDoc.height, srcDoc.resolution, "mcp_temp_export", NewDocumentMode.RGB, DocumentFill.TRANSPARENT);
            app.activeDocument = srcDoc;
            var dupLayer = targetLayer.duplicate(tempDoc, ElementPlacement.PLACEATBEGINNING);
            app.activeDocument = tempDoc;
            dupLayer.visible = true;

            if (trimBounds) {
                tempDoc.trim(TrimType.TRANSPARENT, true, true, true, true);
            }

            var safeName = sanitizeFileName(targetLayer.name) + "_" + targetLayer.id;
            var ext = (formatStr === "JPG" || formatStr === "JPEG") ? ".jpg" : ".png";
            var outFile = new File(outFolder.fsName + "/" + safeName + ext);

            if (ext === ".jpg") {
                var jpgOpts = new JPEGSaveOptions();
                jpgOpts.quality = 10;
                tempDoc.saveAs(outFile, jpgOpts, true, Extension.LOWERCASE);
            } else {
                var pngOpts = new PNGSaveOptions();
                pngOpts.compression = 6;
                tempDoc.saveAs(outFile, pngOpts, true, Extension.LOWERCASE);
            }

            var finalW = Math.round(tempDoc.width.as("px"));
            var finalH = Math.round(tempDoc.height.as("px"));
            tempDoc.close(SaveOptions.DONOTSAVECHANGES);
            app.activeDocument = srcDoc;

            exportedFiles.push(
                '{' +
                '"layer_id": ' + targetLayer.id + ',' +
                '"layer_name": "' + escapeJsonStr(targetLayer.name) + '",' +
                '"file_path": "' + escapeJsonStr(outFile.fsName) + '",' +
                '"width": ' + finalW + ',' +
                '"height": ' + finalH +
                '}'
            );
        }

        app.preferences.rulerUnits = origRuler;
        app.displayDialogs = origDialogs;

        return '{' +
            '"exported_count": ' + exportedFiles.length + ',' +
            '"output_directory": "' + escapeJsonStr(outFolder.fsName) + '",' +
            '"files": [' + exportedFiles.join(",") + ']' +
        '}';
    } catch (err) {
        app.preferences.rulerUnits = origRuler;
        app.displayDialogs = origDialogs;
        return '{"error": "' + escapeJsonStr(err.toString()) + '"}';
    }
})();
"""

# ---------------------------------------------------------------------------
# 3. ドキュメント全体（統合ビュー）のフラット書き出しスクリプト
# ---------------------------------------------------------------------------
JSX_EXPORT_FLATTENED = r"""
(function() {
    if (app.documents.length === 0) {
        return '{"error": "Photoshopで開かれているドキュメントがありません。"}';
    }
    var srcDoc = app.activeDocument;
    var origDialogs = app.displayDialogs;
    app.displayDialogs = DialogModes.NO;

    function escapeJsonStr(s) {
        if (s === null || s === undefined) return "";
        return String(s)
            .replace(/\\/g, "\\\\")
            .replace(/"/g, '\\"')
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n");
    }

    try {
        var outFile = new File("__OUTPUT_FILE_PATH__");
        var outFolder = outFile.parent;
        if (!outFolder.exists) {
            outFolder.create();
        }
        var formatStr = "__FORMAT__".toUpperCase();
        var scalePercent = __SCALE_PERCENT__;

        var tempDoc = srcDoc.duplicate("mcp_flat_export", true);
        if (scalePercent > 0 && scalePercent !== 100) {
            var newW = UnitValue(Math.round(tempDoc.width.as("px") * (scalePercent / 100.0)), "px");
            var newH = UnitValue(Math.round(tempDoc.height.as("px") * (scalePercent / 100.0)), "px");
            tempDoc.resizeImage(newW, newH, null, ResampleMethod.BICUBICAUTOMATIC);
        }

        if (formatStr === "JPG" || formatStr === "JPEG") {
            var jpgOpts = new JPEGSaveOptions();
            jpgOpts.quality = 10;
            tempDoc.saveAs(outFile, jpgOpts, true, Extension.LOWERCASE);
        } else {
            var pngOpts = new PNGSaveOptions();
            pngOpts.compression = 6;
            tempDoc.saveAs(outFile, pngOpts, true, Extension.LOWERCASE);
        }

        var finalW = Math.round(tempDoc.width.as("px"));
        var finalH = Math.round(tempDoc.height.as("px"));
        tempDoc.close(SaveOptions.DONOTSAVECHANGES);
        app.activeDocument = srcDoc;
        app.displayDialogs = origDialogs;

        return '{' +
            '"status": "success",' +
            '"file_path": "' + escapeJsonStr(outFile.fsName) + '",' +
            '"width": ' + finalW + ',' +
            '"height": ' + finalH +
        '}';
    } catch (err) {
        app.displayDialogs = origDialogs;
        return '{"error": "' + escapeJsonStr(err.toString()) + '"}';
    }
})();
"""
