// Dashboard Frontend Logic

document.addEventListener("DOMContentLoaded", () => {
    // State management
    let state = {
        leads: {
            facebook: [],
            linkedin_jobs: [],
            linkedin_posts: []
        },
        currentTab: "overview", // overview, facebook, linkedin-jobs, linkedin-posts
        searchQuery: "",
        statusFilter: "all"
    };

    // DOM Elements
    const navButtons = document.querySelectorAll(".nav-btn");
    const pageTitle = document.getElementById("page-title");
    const pageSubtitle = document.getElementById("page-subtitle");
    const lastUpdated = document.getElementById("last-updated");
    
    // Overview tab elements
    const tabOverview = document.getElementById("tab-overview");
    const totalCount = document.getElementById("total-count");
    const fbCount = document.getElementById("fb-count");
    const liJobsCount = document.getElementById("li-jobs-count");
    const liPostsCount = document.getElementById("li-posts-count");
    const recentLeadsTbody = document.getElementById("recent-leads-tbody");

    // Leads list elements
    const tabLeadsView = document.getElementById("tab-leads-view");
    const leadSearch = document.getElementById("lead-search");
    const filterStatus = document.getElementById("filter-status");
    const clearFiltersBtn = document.getElementById("clear-filters-btn");
    const mainLeadsTable = document.getElementById("main-leads-table");
    const leadsTableThead = document.getElementById("leads-table-thead");
    const leadsTableTbody = document.getElementById("leads-table-tbody");
    const tableEmptyState = document.getElementById("table-empty-state");
    const refreshBtn = document.getElementById("refresh-btn");

    // Load data from leads.json
    async function loadData() {
        try {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Loading...`;
            
            const response = await fetch("leads.json");
            if (!response.ok) {
                throw new Error("Could not fetch leads.json. Please run tracker.py first.");
            }
            
            const data = await response.json();
            
            state.leads.facebook = data.facebook || [];
            state.leads.linkedin_jobs = data.linkedin_jobs || [];
            state.leads.linkedin_posts = data.linkedin_posts || [];
            
            // Set last updated time
            const now = new Date();
            lastUpdated.textContent = `Last updated: ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
            
            updateStats();
            renderRecentLeads();
            
            if (state.currentTab !== "overview") {
                renderLeadsTable();
            }
            
        } catch (error) {
            console.error("Error loading leads:", error);
            lastUpdated.textContent = "Error loading data. Run tracker.py first.";
        } finally {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Reload Data`;
        }
    }

    // Helper to get CRM status from localStorage
    function getLeadStatus(id) {
        return localStorage.getItem(`status_${id}`) || "new";
    }

    // Helper to save CRM status to localStorage
    function setLeadStatus(id, status) {
        localStorage.setItem(`status_${id}`, status);
    }

    // Render dropdown for lead status
    function createStatusDropdown(leadId) {
        const currentStatus = getLeadStatus(leadId);
        const select = document.createElement("select");
        select.className = `status-select status-${currentStatus}`;
        
        const options = [
            { value: "new", label: "New" },
            { value: "contacted", label: "Contacted" },
            { value: "ignored", label: "Ignored" }
        ];
        
        options.forEach(opt => {
            const el = document.createElement("option");
            el.value = opt.value;
            el.textContent = opt.label;
            if (opt.value === currentStatus) el.selected = true;
            select.appendChild(el);
        });

        select.addEventListener("change", (e) => {
            const newStatus = e.target.value;
            setLeadStatus(leadId, newStatus);
            select.className = `status-select status-${newStatus}`;
            
            // If main table or overview needs updating
            if (state.currentTab === "overview") {
                renderRecentLeads();
            } else {
                // If status filter is active, change may hide the row
                if (state.statusFilter !== "all") {
                    renderLeadsTable();
                }
            }
            updateStats(); // Update totals just in case
        });

        return select;
    }

    // Calculate totals
    function updateStats() {
        const fbTotal = state.leads.facebook.length;
        const liJobsTotal = state.leads.linkedin_jobs.length;
        const liPostsTotal = state.leads.linkedin_posts.length;
        const total = fbTotal + liJobsTotal + liPostsTotal;

        totalCount.textContent = total;
        fbCount.textContent = fbTotal;
        liJobsCount.textContent = liJobsTotal;
        liPostsCount.textContent = liPostsTotal;
    }

    // Render Recent 5 Leads on Overview
    function renderRecentLeads() {
        // Collect all leads and add source tag
        const allLeads = [
            ...state.leads.facebook.map(l => ({ ...l, source: "facebook", id: l.post_url })),
            ...state.leads.linkedin_jobs.map(l => ({ ...l, source: "linkedin-jobs", id: l.job_url })),
            ...state.leads.linkedin_posts.map(l => ({ ...l, source: "linkedin-posts", id: l.post_url }))
        ];

        // Sort by date descending (handle empty dates gracefully)
        allLeads.sort((a, b) => {
            const dateA = a.date ? new Date(a.date) : new Date(0);
            const dateB = b.date ? new Date(b.date) : new Date(0);
            return dateB - dateA;
        });

        // Take top 5
        const recent = allLeads.slice(0, 5);
        recentLeadsTbody.innerHTML = "";

        if (recent.length === 0) {
            recentLeadsTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary)">No leads found yet. Run python tracker.py first.</td></tr>`;
            return;
        }

        recent.forEach(lead => {
            const tr = document.createElement("tr");

            // Source cell
            let sourceLabel = "";
            let sourceClass = "";
            if (lead.source === "facebook") {
                sourceLabel = `<i class="fa-brands fa-facebook"></i> FB Groups`;
                sourceClass = "source-facebook";
            } else if (lead.source === "linkedin-jobs") {
                sourceLabel = `<i class="fa-brands fa-linkedin"></i> LI Jobs`;
                sourceClass = "source-linkedin-jobs";
            } else {
                sourceLabel = `<i class="fa-solid fa-paper-plane"></i> LI Posts`;
                sourceClass = "source-linkedin-posts";
            }

            // Description / text details cell
            let details = "";
            let leadLink = "";
            if (lead.source === "facebook") {
                details = lead.post_text;
                leadLink = lead.post_url;
            } else if (lead.source === "linkedin-jobs") {
                details = `${lead.job_title} at ${lead.company} (${lead.location})`;
                leadLink = lead.job_url;
            } else {
                details = `${lead.author_name ? lead.author_name + ': ' : ''}${lead.post_text}`;
                leadLink = lead.post_url;
            }

            // Short date helper
            const d = lead.date ? lead.date.split('T')[0] : "N/A";

            tr.innerHTML = `
                <td><span class="badge ${sourceClass}">${sourceLabel}</span></td>
                <td style="white-space: nowrap; color: var(--text-secondary)">${d}</td>
                <td><div class="text-truncate" title="${details.replace(/"/g, '&quot;')}">${details}</div></td>
                <td class="status-cell"></td>
                <td><a href="${leadLink}" target="_blank" class="lead-link"><i class="fa-solid fa-external-link"></i> Open</a></td>
            `;

            // Append status select
            tr.querySelector(".status-cell").appendChild(createStatusDropdown(lead.id));

            recentLeadsTbody.appendChild(tr);
        });
    }

    // Render Main Table based on current Tab
    function renderLeadsTable() {
        leadsTableThead.innerHTML = "";
        leadsTableTbody.innerHTML = "";
        
        let data = [];
        let keyCol = "";

        // Determine which data to render
        if (state.currentTab === "facebook") {
            data = state.leads.facebook.map(l => ({ ...l, id: l.post_url }));
            keyCol = "post_url";
            
            leadsTableThead.innerHTML = `
                <tr>
                    <th style="width: 140px">Date</th>
                    <th style="width: 250px">Profile Link</th>
                    <th>Post Content</th>
                    <th style="width: 150px">Status</th>
                    <th style="width: 120px">Action</th>
                </tr>
            `;
        } else if (state.currentTab === "linkedin-jobs") {
            data = state.leads.linkedin_jobs.map(l => ({ ...l, id: l.job_url }));
            keyCol = "job_url";
            
            leadsTableThead.innerHTML = `
                <tr>
                    <th style="width: 140px">Date</th>
                    <th style="width: 220px">Job Info</th>
                    <th>Job Excerpt</th>
                    <th style="width: 150px">Status</th>
                    <th style="width: 120px">Action</th>
                </tr>
            `;
        } else if (state.currentTab === "linkedin-posts") {
            data = state.leads.linkedin_posts.map(l => ({ ...l, id: l.post_url }));
            keyCol = "post_url";
            
            leadsTableThead.innerHTML = `
                <tr>
                    <th style="width: 140px">Date</th>
                    <th style="width: 220px">Author</th>
                    <th>Post Text</th>
                    <th style="width: 150px">Status</th>
                    <th style="width: 120px">Action</th>
                </tr>
            `;
        }

        // Apply filters (search & CRM status)
        let filtered = data.filter(item => {
            // 1. Status Filter
            const itemStatus = getLeadStatus(item.id);
            if (state.statusFilter !== "all" && itemStatus !== state.statusFilter) {
                return false;
            }

            // 2. Search Query Filter
            if (state.searchQuery) {
                const query = state.searchQuery.toLowerCase();
                if (state.currentTab === "facebook") {
                    return item.post_text.toLowerCase().includes(query) || item.author_url.toLowerCase().includes(query);
                } else if (state.currentTab === "linkedin-jobs") {
                    return item.job_title.toLowerCase().includes(query) || item.company.toLowerCase().includes(query) || item.location.toLowerCase().includes(query) || item.description.toLowerCase().includes(query);
                } else if (state.currentTab === "linkedin-posts") {
                    return item.post_text.toLowerCase().includes(query) || item.author_name.toLowerCase().includes(query);
                }
            }
            return true;
        });

        // Sort items by date desc
        filtered.sort((a, b) => {
            const dateA = a.date ? new Date(a.date) : new Date(0);
            const dateB = b.date ? new Date(b.date) : new Date(0);
            return dateB - dateA;
        });

        if (filtered.length === 0) {
            mainLeadsTable.style.display = "none";
            tableEmptyState.style.display = "flex";
            return;
        }

        mainLeadsTable.style.display = "table";
        tableEmptyState.style.display = "none";

        filtered.forEach(item => {
            const tr = document.createElement("tr");
            const d = item.date ? item.date.split('T')[0] : "N/A";

            if (state.currentTab === "facebook") {
                const displayAuthor = item.author_url ? item.author_url.split('/')[4] || "View Profile" : "Profile Link";
                tr.innerHTML = `
                    <td style="color: var(--text-secondary); white-space: nowrap">${d}</td>
                    <td><a href="${item.author_url}" target="_blank" class="lead-link"><i class="fa-brands fa-facebook"></i> ${displayAuthor}</a></td>
                    <td><div class="text-truncate" style="max-width: 500px;" title="${item.post_text.replace(/"/g, '&quot;')}">${item.post_text}</div></td>
                    <td class="status-cell"></td>
                    <td><a href="${item.post_url}" target="_blank" class="lead-link"><i class="fa-solid fa-external-link"></i> Open</a></td>
                `;
            } else if (state.currentTab === "linkedin-jobs") {
                tr.innerHTML = `
                    <td style="color: var(--text-secondary); white-space: nowrap">${d}</td>
                    <td>
                        <strong style="display:block;">${item.job_title}</strong>
                        <span style="font-size:12px; color: var(--text-secondary)">${item.company} | ${item.location}</span>
                    </td>
                    <td><div class="text-truncate" style="max-width: 500px;" title="${item.description.replace(/"/g, '&quot;')}">${item.description}</div></td>
                    <td class="status-cell"></td>
                    <td><a href="${item.job_url}" target="_blank" class="lead-link"><i class="fa-solid fa-external-link"></i> Apply</a></td>
                `;
            } else if (state.currentTab === "linkedin-posts") {
                const authorDisplay = item.author_name || "LinkedIn User";
                const authorLink = item.author_url ? `<a href="${item.author_url}" target="_blank" class="lead-link"><i class="fa-brands fa-linkedin"></i> ${authorDisplay}</a>` : `<span style="color:var(--text-secondary)">${authorDisplay}</span>`;
                tr.innerHTML = `
                    <td style="color: var(--text-secondary); white-space: nowrap">${d}</td>
                    <td>${authorLink}</td>
                    <td><div class="text-truncate" style="max-width: 500px;" title="${item.post_text.replace(/"/g, '&quot;')}">${item.post_text}</div></td>
                    <td class="status-cell"></td>
                    <td><a href="${item.post_url}" target="_blank" class="lead-link"><i class="fa-solid fa-external-link"></i> Open</a></td>
                `;
            }

            // Append status select
            tr.querySelector(".status-cell").appendChild(createStatusDropdown(item.id));
            leadsTableTbody.appendChild(tr);
        });
    }

    // Switch Tabs
    function switchTab(tabId) {
        state.currentTab = tabId;

        // Update nav buttons
        navButtons.forEach(btn => {
            if (btn.getAttribute("data-tab") === tabId) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });

        // Reset search/filter inputs when switching tabs
        leadSearch.value = "";
        filterStatus.value = "all";
        state.searchQuery = "";
        state.statusFilter = "all";

        // Display correct tab section
        if (tabId === "overview") {
            tabOverview.classList.add("active");
            tabLeadsView.classList.remove("active");
            pageTitle.textContent = "Dashboard Overview";
            pageSubtitle.textContent = "Real-time leads monitoring for Odoo ERP clients";
            renderRecentLeads();
        } else {
            tabOverview.classList.remove("active");
            tabLeadsView.classList.add("active");
            
            if (tabId === "facebook") {
                pageTitle.textContent = "Facebook Group Leads";
                pageSubtitle.textContent = "Leads parsed and filtered from monitored Facebook ERP Groups";
            } else if (tabId === "linkedin-jobs") {
                pageTitle.textContent = "LinkedIn ERP Job Leads";
                pageSubtitle.textContent = "Recent jobs posted for Odoo/ERP in Egypt, Saudi Arabia, and UAE";
            } else if (tabId === "linkedin-posts") {
                pageTitle.textContent = "LinkedIn Posts & Inquiries";
                pageSubtitle.textContent = "Social posts from individuals looking for ERP implementations";
            }
            
            renderLeadsTable();
        }
    }

    // Event Listeners
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            switchTab(btn.getAttribute("data-tab"));
        });
    });

    leadSearch.addEventListener("input", (e) => {
        state.searchQuery = e.target.value;
        renderLeadsTable();
    });

    filterStatus.addEventListener("change", (e) => {
        state.statusFilter = e.target.value;
        renderLeadsTable();
    });

    clearFiltersBtn.addEventListener("click", () => {
        leadSearch.value = "";
        filterStatus.value = "all";
        state.searchQuery = "";
        state.statusFilter = "all";
        renderLeadsTable();
    });

    refreshBtn.addEventListener("click", loadData);

    // Initial load
    loadData();
});
