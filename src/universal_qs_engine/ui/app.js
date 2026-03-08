document.addEventListener("DOMContentLoaded", () => {
    const state = {
        projectId: null,
        project: null,
    };

    const paneTitle = document.getElementById("pane-title");
    const consoleOutput = document.getElementById("console-output");

    function log(message, type = "info") {
        const line = document.createElement("div");
        line.className = `console-line ${type}`;
        line.textContent = `> ${message}`;
        consoleOutput.prepend(line);
    }

    function setPane(name) {
        document.querySelectorAll(".nav-link").forEach((button) => {
            button.classList.toggle("is-active", button.dataset.pane === name);
        });
        document.querySelectorAll(".pane").forEach((pane) => {
            pane.classList.toggle("is-active", pane.dataset.pane === name);
        });
        paneTitle.textContent = name.charAt(0).toUpperCase() + name.slice(1);
    }

    function setMemberPanel(name) {
        document.querySelectorAll(".template-tab").forEach((button) => {
            button.classList.toggle("is-active", button.dataset.memberPanel === name);
        });
        document.querySelectorAll(".member-panel").forEach((panel) => {
            panel.classList.toggle("is-active", panel.dataset.memberPanel === name);
        });
    }

    function renderList(containerId, items, formatter) {
        const node = document.getElementById(containerId);
        node.innerHTML = "";
        if (!items || !items.length) {
            node.classList.add("empty");
            node.textContent = "No records yet.";
            return;
        }
        node.classList.remove("empty");
        items.forEach((item) => {
            const card = document.createElement("div");
            card.className = "list-item";
            card.innerHTML = formatter(item);
            node.appendChild(card);
        });
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function getComponent(project, componentId) {
        return (project?.takeoff?.components || []).find((item) => item.component_id === componentId) || null;
    }

    function getSegment(project, segmentId) {
        return (project?.takeoff?.segments || []).find((item) => item.segment_id === segmentId) || null;
    }

    function getCandidate(project, candidateId) {
        return (project?.candidates?.components || []).find((item) => item.candidate_id === candidateId) || null;
    }

    function unresolvedBlockOwner(project) {
        return (project?.review_flags || []).some(
            (flag) => flag.export_rule === "block_owner" && flag.resolution_status !== "resolved",
        );
    }

    async function refreshAcceptance() {
        if (!state.projectId) return;
        try {
            const data = await request(`/api/v2/projects/${state.projectId}/acceptance`);
            renderAcceptance(data.evaluation);
        } catch (error) {
            log(`Acceptance check failed: ${error.message}`, "error");
        }
    }

    function renderAcceptance(evaluation) {
        const container = document.getElementById("acceptance-status");
        const overrideForm = document.getElementById("acceptance-override-form");
        
        container.innerHTML = "";
        container.classList.remove("empty");
        
        const statusClass = evaluation.ok ? "success" : "error";
        const statusText = evaluation.ok ? "READY FOR EXPORT" : "ACTION REQUIRED";
        
        let html = `
            <div class="acceptance-header ${statusClass}">
                <strong>${statusText}</strong>
            </div>
            <div class="acceptance-criteria-list">
        `;
        
        for (const [key, passed] of Object.entries(evaluation.criteria)) {
            html += `
                <div class="criterion-item">
                    <span class="criterion-icon">${passed ? "✅" : "❌"}</span>
                    <span class="criterion-label">${key.replaceAll("_", " ")}</span>
                </div>
            `;
        }
        
        html += `</div>`;
        
        if (evaluation.override && evaluation.override.active) {
            html += `
                <div class="acceptance-override-note">
                    <strong>Manual Override Active</strong>
                    <div>Justification: ${escapeHtml(evaluation.override.justification)}</div>
                    <div class="meta">By ${escapeHtml(evaluation.override.author)} on ${evaluation.override.timestamp}</div>
                </div>
            `;
        }
        
        container.innerHTML = html;
        
        // Update Export Owner button
        // Logic: (Evaluation OK OR Override Active) AND No unresolved block_owner flags
        const canExportOwner = evaluation.ok && !unresolvedBlockOwner(state.project);
        document.getElementById("btn-export-owner").disabled = !canExportOwner;
        
        // Show/Hide override form if not OK and no override active
        if (!evaluation.ok && !(evaluation.override && evaluation.override.active)) {
            overrideForm.style.display = "block";
        } else {
            overrideForm.style.display = "none";
        }
    }

    function reviewActionsMarkup(project, flag) {
        const actionBlocks = [];
        const ackComment = flag.ack_comment || "";

        actionBlocks.push(`
            <div class="review-action-block">
                <h4>Audit Note</h4>
                <p>Add context for the review trail. This does not unlock owner export.</p>
                <div class="inline-grid single">
                    <label>Note
                        <textarea id="ack-comment-${flag.flag_id}" placeholder="Explain current status or follow-up.">${escapeHtml(ackComment)}</textarea>
                    </label>
                </div>
                <div class="button-row">
                    <button class="ghost-btn js-ack-flag" data-flag-id="${escapeHtml(flag.flag_id)}">Save Audit Note</button>
                </div>
            </div>
        `);

        if (flag.flag_type === "density_fallback") {
            const component = getComponent(project, flag.target_ref);
            const segment = component ? getSegment(project, component.source_segment_id) : null;
            if (component && segment) {
                actionBlocks.push(`
                    <div class="review-action-block">
                        <h4>Deterministic Segment Override</h4>
                        <p>Apply a measured dimension to segment <code>${escapeHtml(segment.segment_name || segment.segment_id)}</code>. Raw and effective values will both remain in the audit workbook.</p>
                        <div class="inline-grid">
                            <label>Field
                                <select id="override-field-${segment.segment_id}">
                                    <option value="length">length</option>
                                    <option value="width">width</option>
                                    <option value="depth" selected>depth</option>
                                </select>
                            </label>
                            <label>Value
                                <input id="override-value-${segment.segment_id}" type="number" step="0.001" placeholder="0.300">
                            </label>
                        </div>
                        <div class="inline-grid single">
                            <label>Justification
                                <textarea id="override-note-${segment.segment_id}" placeholder="Measured from section or confirmed by engineer."></textarea>
                            </label>
                        </div>
                        <div class="button-row">
                            <button class="primary-btn js-override-segment" data-segment-id="${escapeHtml(segment.segment_id)}" data-flag-id="${escapeHtml(flag.flag_id)}">Apply Override + Rebuild</button>
                        </div>
                    </div>
                `);
            }
        }

        if (flag.flag_type === "candidate_pending_confirmation") {
            const candidate = getCandidate(project, flag.target_ref);
            const proposed = candidate?.proposed_component || {};
            actionBlocks.push(`
                <div class="review-action-block">
                    <h4>Candidate Decision</h4>
                    <p>${escapeHtml(proposed.component_type || candidate?.candidate_id || "Candidate")} · ${escapeHtml(proposed.qty || 0)} ${escapeHtml(proposed.unit || "")} · ${escapeHtml(proposed.source_ref || "")}</p>
                    <div class="inline-grid single">
                        <label>Reason
                            <textarea id="candidate-reason-${flag.target_ref}" placeholder="Record why this candidate is confirmed or rejected."></textarea>
                        </label>
                    </div>
                    <div class="button-row">
                        <button class="primary-btn js-confirm-candidate" data-candidate-id="${escapeHtml(flag.target_ref)}">Confirm Candidate</button>
                        <button class="ghost-btn js-reject-candidate" data-candidate-id="${escapeHtml(flag.target_ref)}">Reject Candidate</button>
                    </div>
                </div>
            `);
        }

        return actionBlocks.length ? `<div class="review-actions">${actionBlocks.join("")}</div>` : "";
    }

    function updateMetrics(project) {
        document.getElementById("project-id").textContent = project?.project_id || "Not created";
        document.getElementById("metric-members").textContent = String(project?.takeoff?.members?.length || 0);
        document.getElementById("metric-segments").textContent = String(project?.takeoff?.segments?.length || 0);
        document.getElementById("metric-components").textContent = String(project?.takeoff?.components?.length || 0);
        document.getElementById("metric-flags").textContent = String(project?.review_flags?.length || 0);
    }

    function renderProject(project) {
        state.project = project;
        state.projectId = project.project_id;
        updateMetrics(project);
        document.getElementById("btn-export-owner").disabled = unresolvedBlockOwner(project);

        renderList("sources-list", project.sources, (item) => `
            <strong>${item.sheet_code || item.filename || item.source_id}</strong>
            <div>${item.discipline} · ${item.role} · ${item.revision || "no revision"}</div>
            <div>${item.path || ""}</div>
        `);

        renderList("rates-list", project.rates, (item) => `
            <strong>${item.item_code || item.rate_id}</strong>
            <div>${item.description || ""}</div>
            <div class="badge-row">
                <span class="badge">${item.rate_context}</span>
                <span class="badge">M ${item.material_rate}</span>
                <span class="badge">L ${item.labor_rate}</span>
            </div>
        `);

        const takeoffItems = [
            ...(project.takeoff.members || []).map((item) => ({
                title: `${item.member_code || item.member_id} · ${item.member_type || "member"}`,
                meta: memberMeta(item),
                ref: item.source_ref || "",
            })),
            ...(project.takeoff.segments || []).map((item) => ({
                title: `${item.segment_name || item.segment_id} · member ${item.member_id || "-"}`,
                meta: `L ${item.length || 0} · W ${item.width || 0} · D ${item.depth || 0} · H ${item.height || 0} · ${item.basis_status || "-"}`,
                ref: item.source_ref || "",
            })),
            ...(project.takeoff.components || []).map((item) => ({
                title: `${item.component_type || item.component_id} · ${item.qty} ${item.unit || ""}`,
                meta: `${item.line_type || "ADD"} · ${item.rate_context || "new"} · ${item.basis_status || "-"} · loss ${item.loss_pct || 0}${item.source_segment_id ? ` · seg ${item.source_segment_id}` : ""}`,
                ref: item.source_ref || "",
            })),
        ];

        renderList("takeoff-list", takeoffItems, (item) => `
            <strong>${item.title}</strong>
            <div>${item.meta}</div>
            <div>${item.ref}</div>
        `);

        renderList("review-list", project.review_flags || [], (item) => `
            <div class="review-item">
            <div>
            <strong>${item.flag_type}</strong>
            <div>${item.message}</div>
            <div class="badge-row">
                <span class="badge ${item.severity === "block_owner" ? "block" : "warn"}">${item.severity}</span>
                <span class="badge">${item.target_ref}</span>${item.resolution_status && item.resolution_status !== "open" ? `<span class="badge">${item.resolution_status}</span>` : ""}
            </div>
            </div>
            ${reviewActionsMarkup(project, item)}
            </div>
        `);
    }

    function memberMeta(item) {
        const memberType = item.member_type || "member";
        if (memberType === "beam") {
            return `${item.discipline || "structure"} · ${item.level || "-"} · span ${item.clear_span || 0} · ${item.section_width || 0}x${item.section_depth || 0} · ${item.basis_status || "-"}`;
        }
        if (memberType === "slab") {
            const firstArea = Array.isArray(item.area_blocks) && item.area_blocks.length ? item.area_blocks[0].area || 0 : 0;
            return `${item.discipline || "structure"} · ${item.level || "-"} · ${item.slab_type || "-"} · thk ${item.thickness || 0} · area ${firstArea} · ${item.basis_status || "-"}`;
        }
        if (memberType === "pedestal") {
            return `${item.discipline || "structure"} · ${item.level || "-"} · ${item.type_ref || "-"} · H ${item.H_to_top_of_beam || 0} · ${item.basis_status || "-"}`;
        }
        return `${item.discipline || "structure"} · ${item.level || "-"} · ${item.basis_status || "-"}`;
    }

    async function addTypedMember(memberType, payload) {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        await request(`/api/v2/projects/${state.projectId}/members/${memberType}`, "POST", payload);
        await refreshProject();
        log(`${memberType} member added.`, "success");
    }

    async function request(path, method = "GET", payload = null) {
        const options = { method, headers: {} };
        if (payload) {
            options.headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(payload);
        }
        const response = await fetch(path, options);
        const data = await response.json();
        if (!response.ok || data.ok === false) {
            throw new Error(data.error?.message || data.error || "Request failed");
        }
        return data;
    }

    async function refreshProject() {
        if (!state.projectId) {
            return;
        }
        const data = await request(`/api/v2/projects/${state.projectId}`);
        renderProject(data.project);
        await refreshAcceptance();
    }

    document.querySelectorAll(".nav-link").forEach((button) => {
        button.addEventListener("click", () => {
            const pane = button.dataset.pane;
            setPane(pane);
            if (pane === "export") {
                refreshAcceptance();
            }
        });
    });

    document.getElementById("btn-create-project").addEventListener("click", async () => {
        try {
            const payload = {
                name: document.getElementById("project-name").value,
                client: document.getElementById("project-client").value,
                site: document.getElementById("project-site").value,
                project_type: document.getElementById("project-type").value,
                factor_mode: document.getElementById("factor-mode").value,
                overhead_rate: parseFloat(document.getElementById("overhead-rate").value || "0.12"),
            };
            const data = await request("/api/v2/projects", "POST", payload);
            renderProject(data.project);
            log(`Project created: ${data.project.project_id}`, "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-import-drawing").addEventListener("click", async () => {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        const fileInput = document.getElementById("import-file");
        if (!fileInput.files.length) {
            log("Select a file first.", "warn");
            return;
        }

        try {
            log("Uploading drawing...", "info");
            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            
            const uploadResp = await fetch("/api/v1/intake/upload", {
                method: "POST",
                body: formData
            });
            const uploadData = await uploadResp.json();
            if (!uploadResp.ok || uploadData.ok === false) {
                throw new Error(uploadData.error?.message || "Upload failed");
            }

            log(`Importing drawing from ${uploadData.file_path}...`, "info");
            const importData = await request(`/api/v2/projects/${state.projectId}/import/drawing`, "POST", {
                file_path: uploadData.file_path,
                scale_factor: parseFloat(document.getElementById("import-scale").value || "0.001"),
                discipline: document.getElementById("import-discipline").value,
                source_label: document.getElementById("import-label").value || "IMPORTED",
            });

            await refreshProject();
            log(`Import complete: ${importData.imported_segments} segments, ${importData.imported_candidates} candidates.`, "success");
            setPane("review");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-source").addEventListener("click", async () => {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        try {
            await request(`/api/v2/projects/${state.projectId}/sources`, "POST", {
                filename: document.getElementById("src-filename").value,
                path: document.getElementById("src-path").value,
                discipline: document.getElementById("src-discipline").value,
                revision: document.getElementById("src-revision").value,
                role: document.getElementById("src-role").value,
                sheet_code: document.getElementById("src-sheet").value,
            });
            await refreshProject();
            log("Source added.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.querySelectorAll(".template-tab").forEach((button) => {
        button.addEventListener("click", () => setMemberPanel(button.dataset.memberPanel));
    });

    document.getElementById("btn-add-beam-member").addEventListener("click", async () => {
        try {
            await addTypedMember("beam", {
                member_code: document.getElementById("beam-member-code").value,
                level: document.getElementById("beam-level").value,
                basis_status: document.getElementById("beam-basis").value,
                source_ref: document.getElementById("beam-source").value,
                grid_ref: document.getElementById("beam-grid-ref").value,
                clear_span: parseFloat(document.getElementById("beam-clear-span").value || "0"),
                section_width: parseFloat(document.getElementById("beam-section-width").value || "0"),
                section_depth: parseFloat(document.getElementById("beam-section-depth").value || "0"),
            });
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-slab-member").addEventListener("click", async () => {
        try {
            await addTypedMember("slab", {
                member_code: document.getElementById("slab-member-code").value,
                level: document.getElementById("slab-level").value,
                basis_status: document.getElementById("slab-basis").value,
                source_ref: document.getElementById("slab-source").value,
                slab_type: document.getElementById("slab-type").value,
                thickness: parseFloat(document.getElementById("slab-thickness").value || "0"),
                area_blocks: [
                    {
                        name: "area_block_1",
                        area: parseFloat(document.getElementById("slab-area").value || "0"),
                    },
                ],
                opening_deductions: [
                    {
                        name: "opening_1",
                        area: parseFloat(document.getElementById("slab-opening").value || "0"),
                    },
                ],
            });
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-pedestal-member").addEventListener("click", async () => {
        try {
            await addTypedMember("pedestal", {
                member_code: document.getElementById("pedestal-member-code").value,
                level: document.getElementById("pedestal-level").value,
                basis_status: document.getElementById("pedestal-basis").value,
                source_ref: document.getElementById("pedestal-source").value,
                type_ref: document.getElementById("pedestal-type-ref").value,
                H_to_top_of_beam: parseFloat(document.getElementById("pedestal-h").value || "0"),
                footing_offset: parseFloat(document.getElementById("pedestal-footing-offset").value || "0.05"),
                main_bar_count: parseFloat(document.getElementById("pedestal-main-bar-count").value || "0"),
                main_bar_dia: parseFloat(document.getElementById("pedestal-main-bar-dia").value || "0"),
                tie_dia: parseFloat(document.getElementById("pedestal-tie-dia").value || "0"),
                tie_spacing: parseFloat(document.getElementById("pedestal-tie-spacing").value || "0"),
                drilled_bar_count: parseFloat(document.getElementById("pedestal-drilled-bar-count").value || "0"),
                drill_depth: parseFloat(document.getElementById("pedestal-drill-depth").value || "0"),
                hilti_count: parseFloat(document.getElementById("pedestal-hilti-count").value || "0"),
            });
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-wall-member").addEventListener("click", async () => {
        try {
            await addTypedMember("wall", {
                member_code: document.getElementById("wall-member-code").value,
                level: document.getElementById("wall-level").value,
                wall_type: document.getElementById("wall-type").value,
                height: parseFloat(document.getElementById("wall-height").value || "0"),
                gross_area: parseFloat(document.getElementById("wall-area").value || "0"),
                basis_status: document.getElementById("wall-basis").value,
                source_ref: document.getElementById("wall-source").value,
            });
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-opening-member").addEventListener("click", async () => {
        try {
            await addTypedMember("opening", {
                member_code: document.getElementById("opening-member-code").value,
                parent_wall_id: document.getElementById("opening-parent-wall").value,
                opening_type: document.getElementById("opening-type").value,
                width: parseFloat(document.getElementById("opening-width").value || "0"),
                height: parseFloat(document.getElementById("opening-height").value || "2.0"),
                area: parseFloat(document.getElementById("opening-area").value || "0"),
                count: parseFloat(document.getElementById("opening-count").value || "1"),
                source_ref: document.getElementById("opening-source").value,
            });
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-mep-member").addEventListener("click", async () => {
        try {
            const memberType = document.getElementById("mep-type").value;
            await addTypedMember(memberType, {
                member_code: document.getElementById("mep-member-code").value,
                level: document.getElementById("mep-level").value,
                item_type: document.getElementById("mep-type").value,
                service_type: document.getElementById("mep-service").value,
                count: parseFloat(document.getElementById("mep-count").value || "0"),
                length: parseFloat(document.getElementById("mep-length").value || "0"),
                source_ref: document.getElementById("mep-source").value,
            });
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-run-aggregate").addEventListener("click", async () => {
        if (!state.projectId) return;
        try {
            log("Running multi-discipline aggregator...", "info");
            const data = await request(`/api/v2/projects/${state.projectId}/aggregate`, "POST");
            await refreshProject();
            log("Aggregation complete and calc graph rebuilt.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-segment").addEventListener("click", async () => {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        try {
            await request(`/api/v2/projects/${state.projectId}/segments`, "POST", {
                member_id: document.getElementById("segment-member-id").value,
                segment_name: document.getElementById("segment-name").value,
                length: parseFloat(document.getElementById("segment-length").value || "0"),
                width: parseFloat(document.getElementById("segment-width").value || "0"),
                depth: parseFloat(document.getElementById("segment-depth").value || "0"),
                height: parseFloat(document.getElementById("segment-height").value || "0"),
                area: parseFloat(document.getElementById("segment-area").value || "0"),
                volume: parseFloat(document.getElementById("segment-volume").value || "0"),
                basis_status: document.getElementById("segment-basis").value,
                source_ref: document.getElementById("segment-source").value,
                formula_text: document.getElementById("segment-formula").value,
            });
            await refreshProject();
            log("Segment added.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-component").addEventListener("click", async () => {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        try {
            await request(`/api/v2/projects/${state.projectId}/components`, "POST", {
                member_id: document.getElementById("component-member-id").value,
                source_segment_id: document.getElementById("component-source-segment-id").value,
                component_type: document.getElementById("component-type").value,
                spec: document.getElementById("component-spec").value,
                qty: parseFloat(document.getElementById("component-qty").value || "0"),
                unit: document.getElementById("component-unit").value,
                loss_pct: parseFloat(document.getElementById("component-loss").value || "0"),
                line_type: document.getElementById("component-line-type").value,
                rate_context: document.getElementById("component-rate-context").value,
                basis_status: document.getElementById("component-basis").value,
                source_ref: document.getElementById("component-source").value,
                abt_charged_override: document.getElementById("component-abt-override").value || null,
                formula_text: document.getElementById("component-formula").value,
            });
            await refreshProject();
            log("Component added.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-add-rate").addEventListener("click", async () => {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        try {
            await request(`/api/v2/projects/${state.projectId}/rates`, "POST", {
                item_code: document.getElementById("rate-code").value,
                description: document.getElementById("rate-desc").value,
                unit: document.getElementById("rate-unit").value,
                rate_context: document.getElementById("rate-context").value,
                material_rate: parseFloat(document.getElementById("rate-mat").value || "0"),
                labor_rate: parseFloat(document.getElementById("rate-lab").value || "0"),
            });
            await refreshProject();
            log("Rate added.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-refresh").addEventListener("click", async () => {
        try {
            await refreshProject();
            log("Project refreshed.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-rebuild").addEventListener("click", async () => {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        try {
            await request(`/api/v2/projects/${state.projectId}/calc-graph/rebuild`, "POST", {});
            await refreshProject();
            log("Calc graph rebuilt.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-export").addEventListener("click", async () => {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        try {
            const data = await request(`/api/v2/projects/${state.projectId}/export/internal`, "POST", {});
            const result = document.getElementById("export-result");
            result.classList.remove("empty");
            result.innerHTML = `
                <div class="list-item">
                    <strong>Internal Trace Workbook</strong>
                    <div><a href="${data.xlsx_url}" target="_blank" rel="noopener noreferrer">${data.xlsx}</a></div>
                    <div><a href="${data.owner_workbook_url}" target="_blank" rel="noopener noreferrer">${data.owner_workbook}</a></div>
                    <div>Kernel Final Bid: ${data.summary.final_bid}</div>
                </div>
            `;
            log("Internal bundle exported.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-export-owner").addEventListener("click", async () => {
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }
        try {
            const data = await request(`/api/v2/projects/${state.projectId}/export/owner`, "POST", {});
            const result = document.getElementById("export-result");
            result.classList.remove("empty");
            result.innerHTML = `
                <div class="list-item">
                    <strong>Owner Workbook</strong>
                    <div><a href="${data.xlsx_url}" target="_blank" rel="noopener noreferrer">${data.xlsx}</a></div>
                    <div>Final Bid: ${data.summary.final_bid}</div>
                </div>
            `;
            log("Owner bundle exported.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("btn-override-acceptance").addEventListener("click", async () => {
        if (!state.projectId) return;
        const justification = document.getElementById("acceptance-justification").value;
        if (!justification) {
            log("Justification required for manual override.", "warn");
            return;
        }
        try {
            await request(`/api/v2/projects/${state.projectId}/acceptance/override`, "POST", {
                justification,
                author: "human_reviewer"
            });
            await refreshAcceptance();
            log("Acceptance override applied.", "success");
        } catch (error) {
            log(error.message, "error");
        }
    });

    document.getElementById("review-list").addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        if (!state.projectId) {
            log("Create a project first.", "warn");
            return;
        }

        try {
            if (target.classList.contains("js-ack-flag")) {
                const flagId = target.dataset.flagId;
                const comment = document.getElementById(`ack-comment-${flagId}`)?.value || "";
                await request(`/api/v2/projects/${state.projectId}/review/ack`, "POST", { flag_id: flagId, comment });
                await refreshProject();
                log(`Audit note saved for ${flagId}.`, "success");
                return;
            }

            if (target.classList.contains("js-override-segment")) {
                const segmentId = target.dataset.segmentId;
                const flagId = target.dataset.flagId;
                const field = document.getElementById(`override-field-${segmentId}`)?.value || "depth";
                const value = parseFloat(document.getElementById(`override-value-${segmentId}`)?.value || "0");
                const justification = document.getElementById(`override-note-${segmentId}`)?.value || "";
                await request(`/api/v2/projects/${state.projectId}/review/override`, "POST", {
                    segment_id: segmentId,
                    field,
                    value,
                    justification,
                    flag_id: flagId,
                });
                await refreshProject();
                log(`Override applied to ${segmentId} (${field}=${value}).`, "success");
                return;
            }

            if (target.classList.contains("js-confirm-candidate")) {
                const candidateId = target.dataset.candidateId;
                const reason = document.getElementById(`candidate-reason-${candidateId}`)?.value || "";
                await request(`/api/v2/projects/${state.projectId}/candidates/components/${candidateId}/confirm`, "POST", { reason });
                await refreshProject();
                log(`Candidate ${candidateId} confirmed.`, "success");
                return;
            }

            if (target.classList.contains("js-reject-candidate")) {
                const candidateId = target.dataset.candidateId;
                const reason = document.getElementById(`candidate-reason-${candidateId}`)?.value || "";
                await request(`/api/v2/projects/${state.projectId}/candidates/components/${candidateId}/reject`, "POST", { reason });
                await refreshProject();
                log(`Candidate ${candidateId} rejected.`, "success");
            }
        } catch (error) {
            log(error.message, "error");
        }
    });

    setPane("setup");
    setMemberPanel("beam");
    log("Authoring-first workspace loaded.", "success");
});
