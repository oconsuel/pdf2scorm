#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple PDF to SCORM converter.
Each PDF page is rendered as an image and becomes a separate SCORM SCO.
No configuration required — just PDF in, SCORM ZIP out.
"""

import zipfile
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom

import fitz  # PyMuPDF


class SimpleConverter:

    def convert(self, pdf_path, output_dir, title=None, scorm_version='2004'):
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        title = title or pdf_path.stem

        temp_dir = output_dir / f"{title}_simple_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            images_dir = temp_dir / 'images'
            images_dir.mkdir()

            image_paths = self._render_pages(pdf_path, images_dir)
            total = len(image_paths)

            if total == 0:
                raise ValueError("PDF не содержит страниц")

            for i, img in enumerate(image_paths, 1):
                html = self._page_html(i, total, img.name, title, scorm_version)
                (temp_dir / f'page_{i}.html').write_text(html, encoding='utf-8')

            (temp_dir / 'SCORM_API_wrapper.js').write_text(
                self._scorm_api_js(), encoding='utf-8'
            )

            manifest = self._manifest(image_paths, title, scorm_version)
            xml_str = minidom.parseString(
                ET.tostring(manifest, encoding='unicode')
            ).toprettyxml(indent="  ")
            (temp_dir / 'imsmanifest.xml').write_text(xml_str, encoding='utf-8')

            zip_path = output_dir / f"{title}_SCORM.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(temp_dir / 'imsmanifest.xml', 'imsmanifest.xml')
                zf.write(temp_dir / 'SCORM_API_wrapper.js', 'SCORM_API_wrapper.js')
                for i in range(1, total + 1):
                    zf.write(temp_dir / f'page_{i}.html', f'page_{i}.html')
                for img in image_paths:
                    zf.write(img, f'images/{img.name}')

            return zip_path
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _render_pages(pdf_path, images_dir):
        doc = fitz.open(pdf_path)
        paths = []
        for idx in range(len(doc)):
            pix = doc[idx].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            out = images_dir / f'page_{idx + 1}.png'
            pix.save(out)
            paths.append(out)
        doc.close()
        return paths

    # ------------------------------------------------------------------
    # HTML per page
    # ------------------------------------------------------------------

    @staticmethod
    def _page_html(page_num, total, image_file, title, scorm_version):
        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Страница {page_num}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100%;overflow:hidden}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#1e293b;display:flex;flex-direction:column}}
.slide{{flex:1;display:flex;align-items:center;justify-content:center;padding:12px;min-height:0}}
.slide img{{max-width:calc(100vw - 40px);max-height:calc(100vh - 60px);border-radius:6px;box-shadow:0 8px 30px rgba(0,0,0,.4);object-fit:contain}}
.footer{{background:#0f172a;color:#94a3b8;padding:8px;text-align:center;font-size:13px;flex-shrink:0}}
</style>
<script src="SCORM_API_wrapper.js"></script>
</head>
<body>
<div class="slide"><img src="images/{image_file}" alt="Страница {page_num}"></div>
<div class="footer">Страница {page_num} из {total}</div>
<script>
(function(){{
    var scorm = pipwerks.SCORM;
    var started = Date.now();
    var done = false;

    function init() {{
        if (done) return;
        scorm.version = "{scorm_version}";
        if (!scorm.init()) return;
        done = true;
        started = Date.now();

        scorm.set("cmi.completion_status", "completed");
        scorm.set("cmi.success_status", "passed");
        scorm.set("cmi.score.scaled", "1");
        scorm.set("cmi.score.raw", "100");
        scorm.set("cmi.score.min", "0");
        scorm.set("cmi.score.max", "100");
        scorm.set("cmi.progress_measure", "1");
        scorm.set("cmi.location", "{page_num}");
        scorm.set("cmi.exit", "suspend");
        scorm.save();
    }}

    window.addEventListener("load", init);

    window.addEventListener("beforeunload", function() {{
        if (!done) return;
        try {{
            var t = Math.floor((Date.now() - started) / 1000);
            var h = Math.floor(t / 3600);
            var m = Math.floor((t % 3600) / 60);
            var s = t % 60;
            scorm.set("cmi.session_time", "PT" + h + "H" + m + "M" + s + "S");
            scorm.save();
        }} catch(e) {{}}
    }});
}})();
</script>
</body>
</html>"""

    # ------------------------------------------------------------------
    # SCORM manifest
    # ------------------------------------------------------------------

    def _manifest(self, image_paths, title, scorm_version):
        safe = title.replace(' ', '_').replace('"', '').replace("'", '')
        m = ET.Element('manifest')
        m.set('identifier', f'SCORM_{safe}')

        if scorm_version == '2004':
            m.set('xmlns', 'http://www.imsglobal.org/xsd/imscp_v1p1')
            m.set('xmlns:adlcp', 'http://www.adlnet.org/xsd/adlcp_v1p3')
            m.set('xmlns:adlseq', 'http://www.adlnet.org/xsd/adlseq_v1p3')
            m.set('xmlns:adlnav', 'http://www.adlnet.org/xsd/adlnav_v1p3')
            m.set('xmlns:imsss', 'http://www.imsglobal.org/xsd/imsss')
            schema_ver = '2004 4th Edition'
            sco_attr = ('adlcp:scormType', 'sco')
        else:
            m.set('xmlns', 'http://www.imsproject.org/xsd/imscp_rootv1p1p2')
            m.set('xmlns:adlcp', 'http://www.adlnet.org/xsd/adlcp_rootv1p2')
            schema_ver = '1.2'
            sco_attr = ('adlcp:scormtype', 'sco')

        md = ET.SubElement(m, 'metadata')
        ET.SubElement(md, 'schema').text = 'ADL SCORM'
        ET.SubElement(md, 'schemaversion').text = schema_ver

        orgs = ET.SubElement(m, 'organizations', default='TOC1')
        org = ET.SubElement(orgs, 'organization', identifier='TOC1')
        ET.SubElement(org, 'title').text = title

        if scorm_version == '2004':
            org_seq = ET.SubElement(org, 'imsss:sequencing')
            ctrl = ET.SubElement(org_seq, 'imsss:controlMode')
            ctrl.set('choice', 'true')
            ctrl.set('choiceExit', 'true')
            ctrl.set('flow', 'true')
            ctrl.set('forwardOnly', 'false')

        resources = ET.SubElement(m, 'resources')

        for i, img in enumerate(image_paths, 1):
            item = ET.SubElement(org, 'item',
                                 identifier=f'ITEM_{i}',
                                 identifierref=f'RES_{i}')
            ET.SubElement(item, 'title').text = f'Страница {i}'

            if scorm_version == '2004':
                item_seq = ET.SubElement(item, 'imsss:sequencing')
                dc = ET.SubElement(item_seq, 'imsss:deliveryControls')
                dc.set('completionSetByContent', 'true')
                dc.set('objectiveSetByContent', 'true')

            res = ET.SubElement(resources, 'resource',
                                identifier=f'RES_{i}',
                                type='webcontent',
                                href=f'page_{i}.html')
            res.set(*sco_attr)
            ET.SubElement(res, 'file', href=f'page_{i}.html')
            ET.SubElement(res, 'file', href='SCORM_API_wrapper.js')
            ET.SubElement(res, 'file', href=f'images/{img.name}')

        return m

    # ------------------------------------------------------------------
    # SCORM API wrapper JS
    # ------------------------------------------------------------------

    @staticmethod
    def _scorm_api_js():
        return r"""var pipwerks={};
pipwerks.SCORM={
    version:null,
    API:{handle:null,isPresent:false},
    connection:{isActive:false},

    init:function(){
        var a=this.getAPI();
        if(!a) return false;
        this.API.handle=a.handle;
        this.API.isPresent=true;
        var ok;
        if(this.version==="2004"){
            ok=this.API.handle.Initialize("");
        }else{
            ok=this.API.handle.LMSInitialize("");
        }
        if(ok==="true"||ok===true){
            this.connection.isActive=true;
            return true;
        }
        return false;
    },

    getAPI:function(){
        var w=window,a=null,n=0;
        while(!a&&n<500){
            try{
                if(w.API_1484_11) a={handle:w.API_1484_11,version:"2004"};
                else if(w.API) a={handle:w.API,version:"1.2"};
            }catch(e){}
            if(!a&&w.parent&&w.parent!==w){w=w.parent;n++;}
            else break;
        }
        if(!a){
            try{
                var op=window.opener;
                while(op&&!a&&n<500){
                    if(op.API_1484_11) a={handle:op.API_1484_11,version:"2004"};
                    else if(op.API) a={handle:op.API,version:"1.2"};
                    if(!a&&op.parent&&op.parent!==op){op=op.parent;n++;}
                    else break;
                }
            }catch(e){}
        }
        return a;
    },

    get:function(p){
        if(!this.connection.isActive) return "";
        try{
            if(this.version==="2004") return String(this.API.handle.GetValue(p));
            return String(this.API.handle.LMSGetValue(p));
        }catch(e){return "";}
    },

    set:function(p,v){
        if(!this.connection.isActive) return false;
        try{
            if(this.version==="2004") return this.API.handle.SetValue(p,String(v));
            return this.API.handle.LMSSetValue(p,String(v));
        }catch(e){return false;}
    },

    save:function(){
        if(!this.connection.isActive) return false;
        try{
            if(this.version==="2004") return this.API.handle.Commit("");
            return this.API.handle.LMSCommit("");
        }catch(e){return false;}
    },

    quit:function(){
        if(!this.connection.isActive) return false;
        this.connection.isActive=false;
        try{
            if(this.version==="2004") return this.API.handle.Terminate("");
            return this.API.handle.LMSFinish("");
        }catch(e){return false;}
    }
};
pipwerks.UTILS={trace:function(){}};"""
