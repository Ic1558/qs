document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('file-upload');
    const dropZone = document.getElementById('drop-zone');
    const uploadList = document.getElementById('upload-list');
    const btnStart = document.getElementById('btn-start');
    const consoleOutput = document.getElementById('console-output');
    
    let uploadedFiles = [];
    let jobId = null;
    let lastComputedItems = [];

    dropZone.addEventListener('click', () => fileUpload.click());
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        handleFiles(dt.files);
    });

    fileUpload.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        uploadedFiles = Array.from(files);
        uploadList.innerHTML = '';
        uploadList.classList.remove('hidden');
        
        uploadedFiles.forEach(f => {
            const el = document.createElement('div');
            el.className = "flex items-center gap-3 p-3 bg-slate-800/80 rounded-lg border border-slate-700";
            el.innerHTML = `
                <svg class="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                <div class="flex-1 overflow-hidden"><p class="text-sm font-medium text-slate-300 truncate">${f.name}</p><p class="text-xs text-slate-500">${(f.size/1024/1024).toFixed(2)} MB</p></div>
            `;
            uploadList.appendChild(el);
        });

        if (uploadedFiles.length > 0) {
            btnStart.classList.remove('opacity-0', 'pointer-events-none', 'translate-y-4');
        }
    }

    function logConsole(msg, type='info') {
        const line = document.createElement('div');
        line.className = type === 'error' ? 'text-red-400' : (type === 'success' ? 'text-emerald-400' : 'text-slate-400');
        line.innerText = `>> ${msg}`;
        consoleOutput.appendChild(line);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    async function setStage(number) {
        document.querySelectorAll('.stage-view').forEach(el => {
            el.classList.remove('active-stage');
            el.classList.add('hidden');
        });
        
        for (let i = 1; i <= 4; i++) {
            const step = document.getElementById(`step-${i}`);
            if (i < number) {
                step.classList.add('is-done');
                step.classList.remove('is-active');
            } else if (i === number) {
                step.classList.add('is-active');
                step.classList.remove('is-done');
            } else {
                step.classList.remove('is-done', 'is-active');
            }
        }

        if (number === 1) {
            document.getElementById('stage-upload').classList.remove('hidden');
            document.getElementById('stage-upload').classList.add('active-stage');
        } else if (number === 2) {
            document.getElementById('stage-processing').classList.remove('hidden');
            setTimeout(() => document.getElementById('stage-processing').classList.add('active-stage'), 50);
        } else if (number === 3) {
            document.getElementById('stage-review').classList.remove('hidden');
            setTimeout(() => document.getElementById('stage-review').classList.add('active-stage'), 50);
        } else if (number === 4) {
            document.getElementById('stage-output').classList.remove('hidden');
            setTimeout(() => document.getElementById('stage-output').classList.add('active-stage'), 50);
        }
    }

    btnStart.addEventListener('click', async () => {
        setStage(2);
        logConsole('Uploading files to local safe runtime...', 'info');

        const formData = new FormData();
        uploadedFiles.forEach(f => formData.append('files', f));

        try {
            const uploadRes = await fetch('/api/v1/intake/upload', {
                method: 'POST',
                body: formData
            });
            const intakeData = await uploadRes.json();
            
            if (!intakeData.ok) throw new Error(intakeData.error?.message || "Upload failed");
            jobId = intakeData.job_id;
            logConsole(`Upload success. Assigned Job ID: ${jobId}`, 'success');

            const hasPdf = intakeData.inputs.some(i => i.type === 'pdf');
            const hasDwg = intakeData.inputs.some(i => ['dwg', 'dxf'].includes(i.type));

            let entities = [];

            if (hasDwg) {
                logConsole('Executing deterministic Vector extraction for DWG...', 'info');
                const dwgRes = await fetch('/api/v1/extract/dwg', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({job_id: jobId, file: intakeData.inputs.find(i => ['dwg', 'dxf'].includes(i.type)).file})
                });
                const dwgData = await dwgRes.json();
                if (!dwgData.ok) {
                    throw new Error(dwgData.error?.message || "DWG Extraction failed");
                }
                entities.push(...(dwgData.entities || []));
                logConsole(`Extracted ${dwgData.entity_count || entities.length} vector entities.`, 'success');
                if (dwgData.generic_count) {
                    logConsole(`Unclassified vector entities: ${dwgData.generic_count}`, 'info');
                }
            }

            let pdfWarnings = [];
            if (hasPdf) {
                logConsole('Executing Vector Extraction for PDF...', 'info');
                const pdfRes = await fetch('/api/v1/extract/pdf', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({job_id: jobId, file: intakeData.inputs.find(i => i.type === 'pdf').file, scale: {scale_factor: 0.05}, vision: {requested: false}})
                });
                const pdfData = await pdfRes.json();
                if (!pdfData.ok) {
                    if (pdfData.error) {
                         throw new Error(pdfData.error.message || "PDF Extraction failed");
                    }
                }
                entities.push(...(pdfData.entities || []));
                if (pdfData.warnings) pdfWarnings.push(...pdfData.warnings);
                logConsole(`Extracted ${pdfData.entity_count || (pdfData.entities ? pdfData.entities.length : 0)} vector entities.`, 'success');
            }

            logConsole('Mapping schema to universal structure...', 'info');
            const mapRes = await fetch('/api/v1/map/schema', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({job_id: jobId, entities})
            });
            const mapData = await mapRes.json();

            logConsole('Running discipline logic (Compute Mode)...', 'info');
            const compRes = await fetch('/api/v1/logic/compute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({job_id: jobId, elements: mapData.elements || [], defaults: {default_height_m: parseFloat(document.getElementById('cfg-height').value)}})
            });
            const compData = await compRes.json();
            lastComputedItems = compData.computed || [];

            if (pdfWarnings.some(w => w.code === 'low_symbol_confidence')) {
                setStage(3); // Review
                const reviewBox = document.getElementById('review-items');
                reviewBox.innerHTML = `
                    <div class="p-4 bg-slate-900 border border-orange-500/30 rounded-lg">
                        <p class="text-sm font-medium text-slate-300">File: PDF Source</p>
                        <p class="text-sm text-slate-400 mt-1">One or more detected symbols are below the 0.95 confidence threshold.</p>
                    </div>
                `;
            } else {
                continueToBoq(jobId, lastComputedItems);
            }
            
        } catch (e) {
            logConsole(`Execution Error: ${e.message}`, 'error');
        }
    });

    document.getElementById('btn-resolve').addEventListener('click', async () => {
        logConsole('Manual review acknowledged. Proceeding to export...', 'info');
        setStage(2);
        continueToBoq(jobId, lastComputedItems);
    });

    async function continueToBoq(jId, computedItems) {
        try {
            logConsole('Generating BOQ / PO-4 / PO-5 / PO-6...', 'info');
            const factorMode = document.getElementById('cfg-factorf').value;
            
            const boqRes = await fetch('/api/v1/boq/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({job_id: jId, computed: computedItems, factor_f: {mode: factorMode === 'auto' ? 'auto' : 'manual'}})
            });
            const boqData = await boqRes.json();
            logConsole(`Factor F matched. Total Cost: ${boqData.po6_total.toLocaleString()} THB`, 'success');

            const exportRes = await fetch('/api/v1/export/xlsx', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({job_id: jId, conflicts_acknowledged: true})
            });
            const exportData = await exportRes.json();
            
            logConsole(`Workbook ready -> ${exportData.xlsx}`, 'success');
            setTimeout(() => setStage(4), 1000);
            
            document.getElementById('btn-download-xlsx').onclick = () => window.open(exportData.xlsx_url || exportData.xlsx, '_blank');
            document.getElementById('btn-download-json').onclick = () => window.open(exportData.json_url || exportData.json, '_blank');

        } catch (e) {
            logConsole(`Export Error: ${e.message}`, 'error');
        }
    }
});
