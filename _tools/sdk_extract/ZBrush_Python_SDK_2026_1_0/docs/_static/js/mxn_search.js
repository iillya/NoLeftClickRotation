/* Contains the ui and search logic used by mxn-search. 
*/

/* Handles all UI interactions of the search page. */
class MxnSearchUiHandler {

    // The number of characters to show before and after a search match.
    static SNIPPET_DISTANCE_VERBOSE = 100;
    static SNIPPET_DISTANCE_COMPACT = 50;

    // CSS classes.
    static CLS_DISABLED_BLUR = "mxn-disabled-blur"
    static CLS_FACETS_CLOSED = "bi-arrow-bar-down"
    static CLS_FACETS_OPEN = "bi-arrow-bar-up"
    static CLS_HELP_CLOSED = "bi-question-square"
    static CLS_HELP_OPEN = "bi-question-square-fill"
    static CLS_HIDDEN = "d-none"
    static CLS_RESULT_SORT_CLASSIFICATION = "bi-text-left"
    static CLS_RESULT_SORT_RELEVANCE = "bi-filter-left"
    static CLS_RESULT_VERBOSE = "bi-card-text"
    static CLS_RESULT_COMPACT = "bi-usb-c"
    static CLS_SEARCH_FUZZY = "bi-funnel"
    static CLS_SEARCH_PAGE = "mxn-search"
    static CLS_SEARCH_STRICT = "bi-funnel-fill"
    static CLS_TAGS = "mxn-tags"
    static CLS_TARGET = "toggle-target"

    // IDs of HTML elements.
    static ID_BTN_RESULT_SORTING = "btn-result-sorting"
    static ID_BTN_RESULT_VERBOSITY = "btn-result-verbosity"
    static ID_BTN_SEARCH_FACETS_VISIBILITY = "btn-search-facets-visibility"
    static ID_BTN_SEARCH_FUZZY = "btn-search-fuzzy"
    static ID_BTN_SEARCH_HELP_VISIBILITY = "btn-search-help-visibility"
    static ID_BTN_SEARCH_JOIN = "btn-search-join"
    static ID_PAGE = "page-content"
    static ID_SEARCH_BAR_TOP = "search-bar-top"
    static ID_SEARCH_FORM = "search-form"
    static ID_SEARCH_HELP = "search-help"
    static ID_SEARCH_INFO = "search-info"
    static ID_SEARCH_OVERLAY = "search-overlay"
    static ID_SEARCH_RESULTS = "search-results"

    // Names.
    static NME_CONTEXTS = "c"
    static NME_DOMAINS = "d"
    static NME_ENTITIES = "e"
    static NME_STORAGE = "mxn-search-settings"
    static QUERY_SETTINGS = "s"
    static QUERY_VALUE = "q"
    static LBL_JOIN_AND = "AND"
    static LBL_JOIN_OR = "OR"

    // Help texts.
    static HLP_FACETS_HIDE = "Hide search facets"
    static HLP_FACETS_SHOW = "Show search facets"
    static HLP_HELP_HIDE = "Hides the search help panel"
    static HLP_HELP_SHOW = "Shows the search help panel"
    static HLP_SEARCH_FUZZY = "Fuzzy search"
    static HLP_SEARCH_JOIN_AND = "Joins search terms with AND"
    static HLP_SEARCH_JOIN_OR = "Joins search terms with OR"
    static HLP_SEARCH_STRICT = "Strict search"
    static HLP_SORT_CLASSIFICATION = "Sorts by entity type and relevance"
    static HLP_SORT_RELEVANCE = "Sorts by relevance only"
    static HLP_RESULT_COMPACT = "Compact result view"
    static HLP_RESULT_VERBOSE = "Detailed result view"

    // Values for the facets. Must be powers of two and match the values in mxn_search_indexer.py.
    static VAL_API = 1 << 0
    static VAL_PAGES = 1 << 1
    static VAL_EXAMPLES = 1 << 2

    static VAL_TEXT = 1 << 0
    static VAL_HEADING = 1 << 1
    static VAL_CODE = 1 << 2
    static VAL_NAME = 1 << 3
    static VAL_SIGNATURE = 1 << 4
    static VAL_METADATA = 1 << 5

    static VAL_GENERIC = 1 << 0
    static VAL_MODULE = 1 << 1
    static VAL_CLASS = 1 << 2
    static VAL_METHOD = 1 << 3
    static VAL_FUNCTION = 1 << 4
    static VAL_ATTRIBUTE = 1 << 5

    // Values for other modes.
    static VAL_SEARCH_FACETS_OPEN = 1 << 0
    static VAL_SEARCH_JOIN_AND = 1 << 1
    static VAL_SEARCH_FUZZY = 1 << 2
    static VAL_SEARCH_VERBOSE = 1 << 3
    static VAL_SEARCH_SORT_CLASSIFICATION = 1 << 4

    // These are used to map the facet values to their labels in the UI.
    static MAP_DOMAIN_VALUE_TO_LABEL = {
        [MxnSearchUiHandler.VAL_API]: "API",
        [MxnSearchUiHandler.VAL_PAGES]: "Manuals",
        [MxnSearchUiHandler.VAL_EXAMPLES]: "Examples"
    };
    
    static MAP_ENTITY_VALUE_TO_LABEL = {
        [MxnSearchUiHandler.VAL_GENERIC]: "Page",
        [MxnSearchUiHandler.VAL_MODULE]: "Module",
        [MxnSearchUiHandler.VAL_CLASS]: "Class",
        [MxnSearchUiHandler.VAL_METHOD]: "Method",
        [MxnSearchUiHandler.VAL_FUNCTION]: "Function",
        [MxnSearchUiHandler.VAL_ATTRIBUTE]: "Attribute"
    };

    static MAP_CONTEXT_VALUE_TO_LABEL = {
        [MxnSearchUiHandler.VAL_TEXT]: "Text",
        [MxnSearchUiHandler.VAL_HEADING]: "Heading",
        [MxnSearchUiHandler.VAL_CODE]: "Code",
        [MxnSearchUiHandler.VAL_NAME]: "Name",
        [MxnSearchUiHandler.VAL_SIGNATURE]: "Signature",
        [MxnSearchUiHandler.VAL_METADATA]: "Metadata"
    };

    static MAP_ENTITY_VALUE_TO_PREFIX = {
        [MxnSearchUiHandler.VAL_GENERIC]: "P",
        [MxnSearchUiHandler.VAL_MODULE]: "Mod",
        [MxnSearchUiHandler.VAL_CLASS]: "C",
        [MxnSearchUiHandler.VAL_METHOD]: "M",
        [MxnSearchUiHandler.VAL_FUNCTION]: "F",
        [MxnSearchUiHandler.VAL_ATTRIBUTE]: "A"
    };

    /* Gets the state of the checkboxes of a given search #facet group and combines them into a single 
       integer flag. */
    static GetSearchFacets(facet) {

        let value = 0;
        const checkboxes = document.querySelectorAll('input[type="checkbox"][name="' + facet + '"]');
        checkboxes.forEach(function (cb) {
            if (cb.checked) 
                value |= parseInt(cb.value, 10);
        });

        return value;
    }

    /* Sets the checked state of the checkboxes of a given search #facet group based on the bits in the 
       integer #flag. */
    static SetSearchFacets(facet, flag) {

        if (flag === undefined) 
            return;

        let checkboxes = document.querySelectorAll('input[type="checkbox"][name="' + facet + '"]');
        checkboxes.forEach(function (cb) {
            let v = parseInt(cb.value, 10);
            cb.checked = (flag & v) === v;
        });
    }

    /* Gets the items in the search that are not facets, such as sorting, verbosity, and more. */
    static GetSearchModes() {

        const isSearchPage = MxnSearchUiHandler.IsMainSearchPage();
        let result = 0;
        let firstTarget = document.querySelectorAll(`.${MxnSearchUiHandler.CLS_TARGET}`);
        let btnSearchJoin = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_JOIN);
        let btnSearchFuzzy = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FUZZY);
        let btnSorting = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_SORTING);
        let btnVerbosity = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_VERBOSITY);
        if (!btnSorting || !btnSearchFuzzy || !btnSearchJoin || !firstTarget || !btnVerbosity || 
            firstTarget.length === 0) {
            console.error("Cannot get modes: Did not find all mode elements.");
            return result;
        }
        
        firstTarget = firstTarget[0];
        if (firstTarget.classList.contains(MxnSearchUiHandler.CLS_HIDDEN))
            result |= MxnSearchUiHandler.VAL_SEARCH_FACETS_OPEN;

        if (btnSearchJoin.textContent === MxnSearchUiHandler.LBL_JOIN_AND)
            result |= MxnSearchUiHandler.VAL_SEARCH_JOIN_AND;

        if (btnSorting.classList.contains(MxnSearchUiHandler.CLS_RESULT_SORT_CLASSIFICATION))
            result |= MxnSearchUiHandler.VAL_SEARCH_SORT_CLASSIFICATION;

        if (btnSearchFuzzy.classList.contains(MxnSearchUiHandler.CLS_SEARCH_FUZZY))
            result |= MxnSearchUiHandler.VAL_SEARCH_FUZZY;

        // We only store the verbosity setting on the main search page, in the quick search we just
        // copy the existing state.
        if (isSearchPage && (btnVerbosity.classList.contains(MxnSearchUiHandler.CLS_RESULT_VERBOSE))) {
            result |= MxnSearchUiHandler.VAL_SEARCH_VERBOSE;
        } else if (!isSearchPage) {
            const setting = localStorage.getItem(MxnSearchUiHandler.NME_STORAGE);
            const modes = setting ? JSON.parse(setting).modes : 0;
            if (modes && (modes & MxnSearchUiHandler.VAL_SEARCH_VERBOSE))
                result |= MxnSearchUiHandler.VAL_SEARCH_VERBOSE;
        }

        return result;
    }

    /* Sets the search items that are not facets, such as sorting, verbosity, and more, based on the
       bits in the integer #flag. */
    static RestoreSearchModes(flag) {

        if (flag === undefined) 
            return;
        
        const isSearchPage = MxnSearchUiHandler.IsMainSearchPage();
        let btnFacets = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FACETS_VISIBILITY);
        let btnSearchJoin = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_JOIN);
        let btnSearchFuzzy = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FUZZY);
        let btnSorting = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_SORTING);
        let btnVerbosity = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_VERBOSITY);
        if (!btnSorting || !btnSearchFuzzy || !btnSearchJoin || !btnFacets || !btnVerbosity) {
            console.error("Cannot set modes: Did not find all modes elements.");
            return;
        }

        if ((flag & MxnSearchUiHandler.VAL_SEARCH_FACETS_OPEN) === 0) {
            MxnSearchUiHandler.ToggleFacetsVisibility.call(btnFacets);
        }

        if ((flag & MxnSearchUiHandler.VAL_SEARCH_JOIN_AND) === 0) {
            btnSearchJoin.textContent = MxnSearchUiHandler.LBL_JOIN_OR;
        } else {
            btnSearchJoin.textContent = MxnSearchUiHandler.LBL_JOIN_AND;
        }

        if ((flag & MxnSearchUiHandler.VAL_SEARCH_FUZZY) === 0) {
            btnSearchFuzzy.classList.remove(MxnSearchUiHandler.CLS_SEARCH_FUZZY);
            btnSearchFuzzy.classList.add(MxnSearchUiHandler.CLS_SEARCH_STRICT);
        } else {
            btnSearchFuzzy.classList.remove(MxnSearchUiHandler.CLS_SEARCH_STRICT);
            btnSearchFuzzy.classList.add(MxnSearchUiHandler.CLS_SEARCH_FUZZY);
        }

        if ((flag & MxnSearchUiHandler.VAL_SEARCH_SORT_CLASSIFICATION) === 0) {
            btnSorting.classList.remove(MxnSearchUiHandler.CLS_RESULT_SORT_CLASSIFICATION);
            btnSorting.classList.add(MxnSearchUiHandler.CLS_RESULT_SORT_RELEVANCE);
        } else {
            btnSorting.classList.remove(MxnSearchUiHandler.CLS_RESULT_SORT_RELEVANCE);
            btnSorting.classList.add(MxnSearchUiHandler.CLS_RESULT_SORT_CLASSIFICATION);
        }

        if (isSearchPage) { // We only restore verbosity on the main search page. 
            if ((flag & MxnSearchUiHandler.VAL_SEARCH_VERBOSE) === 0) {
                btnVerbosity.classList.remove(MxnSearchUiHandler.CLS_RESULT_VERBOSE);
                btnVerbosity.classList.add(MxnSearchUiHandler.CLS_RESULT_COMPACT);
            } else {
                btnVerbosity.classList.remove(MxnSearchUiHandler.CLS_RESULT_COMPACT);
                btnVerbosity.classList.add(MxnSearchUiHandler.CLS_RESULT_VERBOSE);
            }
        }
    }

    /* Loads all stored search settings from local storage and URL parameters. */
    static LoadSearchSettings() {

        // Parse and set the search query from the URL parameters.
        let urlParams = new URLSearchParams(window.location.search);
        let q = urlParams.get(MxnSearchUiHandler.QUERY_VALUE);
        if (q) {
            let input = document.querySelector(
                `#${MxnSearchUiHandler.ID_SEARCH_FORM} input[name="${MxnSearchUiHandler.QUERY_VALUE}"]`);
            if (input) input.value = q;
        }

        // Load the locally stored settings and then override them with the URL parameters.
        let settings = localStorage.getItem(MxnSearchUiHandler.NME_STORAGE);
        try {
            settings = JSON.parse(settings) || {};
        } catch (e) {
            settings = {};
            console.error("Failed to parse search settings from local storage.");
        }

        const uriSettings = urlParams.get(MxnSearchUiHandler.QUERY_SETTINGS);
        const parts = uriSettings ? uriSettings.split(".") : null;
        if (uriSettings && parts && parts.length === 4) {
            settings.modes = parseInt(parts[0], 10);
            settings.domains = parseInt(parts[1], 10);
            settings.entities = parseInt(parts[2], 10);
            settings.contexts = parseInt(parts[3], 10);
        }

        MxnSearchUiHandler.RestoreSearchModes(settings.modes);
        MxnSearchUiHandler.SetSearchFacets(MxnSearchUiHandler.NME_DOMAINS, settings.domains);
        MxnSearchUiHandler.SetSearchFacets(MxnSearchUiHandler.NME_ENTITIES, settings.entities);
        MxnSearchUiHandler.SetSearchFacets(MxnSearchUiHandler.NME_CONTEXTS, settings.contexts);
        MxnSearchUiHandler.SetBubbleHelp();
    }

    /* Saves the current search settings to local storage and updates the URL. */
    static SaveSearchSettings() {

        // Get the currently set facets and modes and store them.
        let form = document.getElementById(MxnSearchUiHandler.ID_SEARCH_FORM);
        if (!form) {
            console.error("Search form not found.");
            return;
        }

        const domains = MxnSearchUiHandler.GetSearchFacets(MxnSearchUiHandler.NME_DOMAINS);
        const entities = MxnSearchUiHandler.GetSearchFacets(MxnSearchUiHandler.NME_ENTITIES);
        const contexts = MxnSearchUiHandler.GetSearchFacets(MxnSearchUiHandler.NME_CONTEXTS);
        localStorage.setItem(MxnSearchUiHandler.NME_STORAGE, JSON.stringify({
            modes: MxnSearchUiHandler.GetSearchModes(),
            domains: domains,
            entities: entities,
            contexts: contexts
        }));
    
        // Update the URL to reflect the current settings.
        MxnSearchUiHandler.SetSearchUri("replace");
    }

    /* Toggles the visibility of the facet groups. */
    static ToggleFacetsVisibility() {

        let btn = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FACETS_VISIBILITY);
        if (!btn) {
            console.error("Facet toggle button not found.");
            return;
        }

        btn.classList.toggle(MxnSearchUiHandler.CLS_FACETS_CLOSED);
        btn.classList.toggle(MxnSearchUiHandler.CLS_FACETS_OPEN);
        let state = btn.classList.contains(MxnSearchUiHandler.CLS_FACETS_OPEN);
        btn.setAttribute("title", state ? MxnSearchUiHandler.HLP_FACETS_HIDE : MxnSearchUiHandler.HLP_FACETS_SHOW);

        document.querySelectorAll(`.${MxnSearchUiHandler.CLS_TARGET}`).forEach(function (el) {
            if (state) el.classList.remove(MxnSearchUiHandler.CLS_HIDDEN);
            else el.classList.add(MxnSearchUiHandler.CLS_HIDDEN);
        });

        MxnSearchUiHandler.SetSearchUri("replace");
    }

    /* Toggles the visibility of the search help section. */
    static ToggleShowHelp() {

        let help = document.getElementById(MxnSearchUiHandler.ID_SEARCH_HELP);
        let btn = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_HELP_VISIBILITY);
        if (!help || !btn) {
            console.error("Help section or button not found.");
            return;
        }

        let state = btn.classList.contains(MxnSearchUiHandler.CLS_HELP_OPEN);
        help.classList.toggle("d-none");
        btn.setAttribute("title", state ? MxnSearchUiHandler.HLP_HELP_SHOW : MxnSearchUiHandler.HLP_HELP_HIDE);
        btn.classList.toggle(MxnSearchUiHandler.CLS_HELP_OPEN);
        btn.classList.toggle(MxnSearchUiHandler.CLS_HELP_CLOSED);
    }

    /* Toggles between OR and AND for joining the search terms and saves the settings. */
    static ToggleSearchJoin() {

        let btn = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_JOIN);
        if (!btn) {
            console.error("Search join button not found.");
            return;
        }

        let state = btn.textContent === MxnSearchUiHandler.LBL_JOIN_AND;
        btn.textContent = state ? MxnSearchUiHandler.LBL_JOIN_OR : MxnSearchUiHandler.LBL_JOIN_AND;
        btn.setAttribute("title", state ? MxnSearchUiHandler.HLP_SEARCH_JOIN_OR : 
                                          MxnSearchUiHandler.HLP_SEARCH_JOIN_AND);

        MxnSearchUiHandler.SaveSearchSettings();
    }

    /* Toggles the search result width between fuzzy and strict and saves the settings. */
    static ToggleSearchFuzzy() {

        let btn = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FUZZY);
        if (!btn) {
            console.error("Search fuzzy button not found.");
            return;
        }

        btn.classList.toggle(MxnSearchUiHandler.CLS_SEARCH_STRICT);
        btn.classList.toggle(MxnSearchUiHandler.CLS_SEARCH_FUZZY);
        let state = btn.classList.contains(MxnSearchUiHandler.CLS_SEARCH_STRICT);
        btn.setAttribute("title", state ? MxnSearchUiHandler.HLP_SEARCH_STRICT : MxnSearchUiHandler.HLP_SEARCH_FUZZY);

        MxnSearchUiHandler.SaveSearchSettings();
    }

    /* Toggles the result sorting between classification and relevance. */
    static ToggleResultSorting() {

        let btn = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_SORTING);
        if (!btn) {
            console.error("Result sorting button not found.");
            return;
        }

        btn.classList.toggle(MxnSearchUiHandler.CLS_RESULT_SORT_CLASSIFICATION);
        btn.classList.toggle(MxnSearchUiHandler.CLS_RESULT_SORT_RELEVANCE);
        let state = btn.classList.contains(MxnSearchUiHandler.CLS_RESULT_SORT_CLASSIFICATION);
        btn.setAttribute("title", state ? MxnSearchUiHandler.HLP_SORT_CLASSIFICATION : 
                                          MxnSearchUiHandler.HLP_SORT_RELEVANCE);

        MxnSearchUiHandler.SaveSearchSettings();
    }

    /* Toggles the result verbosity between verbose and compact, or sets it to a specific state. */
    static SetOrToggleResultVerbosity(sender, state = null) {
        const btn = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_VERBOSITY);
        if (!btn) {
            console.error("Result verbosity button not found.");
            return;
        }

        // If no state is provided, toggle between verbose and compact
        if (state === null) {
            btn.classList.toggle(MxnSearchUiHandler.CLS_RESULT_VERBOSE);
            btn.classList.toggle(MxnSearchUiHandler.CLS_RESULT_COMPACT);
        } 
        // If a state is provided, validate and set it
        else if (state === MxnSearchUiHandler.CLS_RESULT_VERBOSE || state === MxnSearchUiHandler.CLS_RESULT_COMPACT) {
            btn.classList.remove(MxnSearchUiHandler.CLS_RESULT_VERBOSE, MxnSearchUiHandler.CLS_RESULT_COMPACT);
            btn.classList.add(state);
        } 
        // Log an error for invalid states
        else {
            console.error(`Invalid state provided for SetOrToggleResultVerbosity: ${state}`);
            return;
        }

        // Update the button's title based on the current state
        const isVerbose = btn.classList.contains(MxnSearchUiHandler.CLS_RESULT_VERBOSE);
        btn.setAttribute("title", isVerbose ? MxnSearchUiHandler.HLP_RESULT_VERBOSE : MxnSearchUiHandler.HLP_RESULT_COMPACT);

        // Save the settings
        MxnSearchUiHandler.SaveSearchSettings();
    }

    /* Toggles a single facet checkbox and saves the settings. */
    static ToggleFacet(checkbox) {

        if (!checkbox) {
            console.error("Facet checkbox not found.");
            return;
        }

        MxnSearchUiHandler.SaveSearchSettings();
        MxnSearchHandler.SearchAndOutput();
    }

    /* Shows or hides the search overlay. */
    static ToggleSearchOverlay(show) {

        let page = document.getElementById(MxnSearchUiHandler.ID_PAGE);
        let overlay = document.getElementById(MxnSearchUiHandler.ID_SEARCH_OVERLAY);
        if (!page || !overlay) {
            console.error("Page content or search overlay not found.");
            return;
        }

        page.classList.toggle(MxnSearchUiHandler.CLS_DISABLED_BLUR, show);
        if (show) {
            overlay.classList.remove(MxnSearchUiHandler.CLS_HIDDEN);
        } else {
            overlay.classList.add(MxnSearchUiHandler.CLS_HIDDEN);
        }
    }

    /* Sets the bubble help of all buttons to their appropriate state. 
    
       This should usually be only called on load, otherwise these will update on their own.*/
    static SetBubbleHelp() {

        let btnJoin = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_JOIN);
        let btnFacets = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FACETS_VISIBILITY);
        let btnSorting = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_SORTING);
        let btnFuzzy = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FUZZY);
        let btnHelp = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_HELP_VISIBILITY);
        let btnVerbosity = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_VERBOSITY);
        if (!btnJoin || !btnFacets || !btnSorting || !btnFuzzy || !btnHelp || !btnVerbosity) {
            console.error("One or more buttons for bubble help updates not found.");
            return;
        }

        btnJoin.setAttribute("title", btnJoin.textContent === MxnSearchUiHandler.LBL_JOIN_AND ? 
            MxnSearchUiHandler.HLP_SEARCH_JOIN_AND : MxnSearchUiHandler.HLP_SEARCH_JOIN_OR);
        btnFacets.setAttribute("title", btnFacets.classList.contains(MxnSearchUiHandler.CLS_FACETS_OPEN) ? 
            MxnSearchUiHandler.HLP_FACETS_HIDE : MxnSearchUiHandler.HLP_FACETS_SHOW);
        btnSorting.setAttribute("title", btnSorting.classList.contains(MxnSearchUiHandler.CLS_RESULT_SORT_CLASSIFICATION) ? 
            MxnSearchUiHandler.HLP_SORT_CLASSIFICATION : MxnSearchUiHandler.HLP_SORT_RELEVANCE);
        btnFuzzy.setAttribute("title", btnFuzzy.classList.contains(MxnSearchUiHandler.CLS_SEARCH_STRICT) ?
            MxnSearchUiHandler.HLP_SEARCH_STRICT : MxnSearchUiHandler.HLP_SEARCH_FUZZY);
        btnHelp.setAttribute("title", MxnSearchUiHandler.HLP_HELP_SHOW);
        btnVerbosity.setAttribute("title", btnVerbosity.classList.contains(MxnSearchUiHandler.CLS_RESULT_VERBOSE) ?
            MxnSearchUiHandler.HLP_RESULT_VERBOSE : MxnSearchUiHandler.HLP_RESULT_COMPACT);

    }

    /* Injects a shortcut hint into the search input field. */
    static InjectSearchShortcutHint() {

        const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.userAgent);
        const input = document.getElementById("search-input");
        const wrapper = document.getElementById("search-input-wrapper");
        if (!input || !wrapper) {
            console.error("Search input or wrapper not found.");
            return;
        }

        // Create shortcut hint element as a single button-like div
        const shortcutHint = document.createElement("div");
        shortcutHint.classList.add("mxn-shortcut-icon");

        // Set the text content as a single string
        const shortcut = isMac ? "Cmd + Shift + F" : "Ctrl + Shift + F";
        shortcutHint.textContent = shortcut;

        wrapper.appendChild(shortcutHint);

        // Hide hint when input is focused or has content
        const toggleHint = () => {
            const shouldHide = input === document.activeElement || input.value.length > 0;
            shortcutHint.classList.toggle("hidden", shouldHide);
        };

        input.addEventListener("focus", toggleHint);
        input.addEventListener("blur", toggleHint);
        input.addEventListener("input", toggleHint);

        // Set simpler placeholder
        input.placeholder = "Search ...";
    }

    /* Clears the search results but does not touch the query. */
    static ClearResults(count = 0) {

        const info = document.getElementById(MxnSearchUiHandler.ID_SEARCH_INFO);
        const container = document.getElementById(MxnSearchUiHandler.ID_SEARCH_RESULTS);
        if (!info || !container) return;

        container.innerHTML = "";
        info.textContent = `Found ${count} result${count === 1 ? "" : "s"}.`;
    }

    /* Resets the search input field and clears the results. */
    static ClearQuery() {

        const searchInput = document.getElementById(MxnSearchUiHandler.ID_SEARCH_BAR_TOP);
        if (searchInput) {
            searchInput.value = "";
        }
    }

    /* Focuses the search input field at the top of the page. */
    static FocusSearchInput() {

        const searchInput = document.getElementById(MxnSearchUiHandler.ID_SEARCH_BAR_TOP);
        if (searchInput) {
            searchInput.focus();
        }
    }

    /* Returns true if we are currently in verbose mode. */
    static IsVerboseMode() {

        const btnVerbosity = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_VERBOSITY);
        if (!btnVerbosity) {
            console.error("Result verbosity button not found.");
            return false;
        }

        return btnVerbosity.classList.contains(MxnSearchUiHandler.CLS_RESULT_VERBOSE);
    }

    /* Returns true if we are currently on the main search page. */
    static IsMainSearchPage() {
        const page = document.getElementById(MxnSearchUiHandler.ID_PAGE);
        return page && page.classList.contains(MxnSearchUiHandler.CLS_SEARCH_PAGE);
    }

    /* Sets the search URI based on the current form input and selected checkboxes. */
    static SetSearchUri(mode = "navigate") {

        const searchField = document.getElementById(MxnSearchUiHandler.ID_SEARCH_BAR_TOP);
        if (!searchField) {
            console.error("Search input field not found.");
            return;
        }
        
        let params = new URLSearchParams();
        const target = searchField.getAttribute("data-target");
        const query = searchField.value ?? "";
        const modes = MxnSearchUiHandler.GetSearchModes();
        const domains = MxnSearchUiHandler.GetSearchFacets(MxnSearchUiHandler.NME_DOMAINS);
        const entities = MxnSearchUiHandler.GetSearchFacets(MxnSearchUiHandler.NME_ENTITIES);
        const contexts = MxnSearchUiHandler.GetSearchFacets(MxnSearchUiHandler.NME_CONTEXTS);
    
        params.set(MxnSearchUiHandler.QUERY_VALUE, query);
        params.set(MxnSearchUiHandler.QUERY_SETTINGS, [modes, domains, entities, contexts].join("."));
    
        // Only update the URL without reloading the page if mode is "replace". Only do this on the
        // search page itself, i.e., when target is "#".
        if (mode === "replace" && target === "#") {
            let newurl = (window.location.protocol + "//" + window.location.host +
                window.location.pathname + "?" + params.toString());
            window.history.replaceState({ path: newurl }, "", newurl);
        }
        // otherwise navigate to the new URL
        else if (mode === "navigate") {
            const baseUrl = target === "#" ? window.location.pathname: target;
            window.location.href = baseUrl + "?" + params.toString();
        }
    }
    
    /* Called when the search form is being submitted to perform the search and output the results. */
    static OnSubmitSearchForm(event) {

        event.preventDefault();
        MxnSearchUiHandler.SaveSearchSettings();
        MxnSearchUiHandler.SetSearchUri("navigate");
    }

    /* Handles keyboard events for global search shortcuts. */
    static OnKeyboardEvent(event) {

        const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.userAgent);
        const modifierKey = isMac ? event.metaKey : event.ctrlKey;

        // Check for Ctrl/Cmd + Shift + F
        if (modifierKey && event.shiftKey && event.key.toLowerCase() === 'f') {
            event.preventDefault();
            MxnSearchUiHandler.ToggleSearchOverlay(true);
            MxnSearchUiHandler.FocusSearchInput();
        }

        // Check for Escape key to close the overlay
        if (event.key === 'Escape') {
            const overlay = document.getElementById(MxnSearchUiHandler.ID_SEARCH_OVERLAY);
            if (overlay && !overlay.classList.contains(MxnSearchUiHandler.CLS_HIDDEN)) {
                MxnSearchUiHandler.ToggleSearchOverlay(false);
                MxnSearchUiHandler.ClearQuery();
                MxnSearchUiHandler.ClearResults();
                MxnSearchUiHandler.SetOrToggleResultVerbosity(null, MxnSearchUiHandler.CLS_RESULT_COMPACT);
            }
        }
    }

    /* Attach the search UI by setting up event listeners. */
    static Attach() {

        // Restore the search state from the URL and local storage.
        MxnSearchUiHandler.LoadSearchSettings();

         // Handle the search facets visibility button.
        const toggleOptionsBtn = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FACETS_VISIBILITY);
        if (toggleOptionsBtn) {
            toggleOptionsBtn.addEventListener("click", MxnSearchUiHandler.ToggleFacetsVisibility);
        }

        // Handle changes to the checkboxes to save the settings.
        document.querySelectorAll(
            `#${MxnSearchUiHandler.ID_SEARCH_FORM} input[type="checkbox"]`).forEach(function (cb) {
            cb.addEventListener("change", MxnSearchUiHandler.ToggleFacet.bind(null, cb));
        });

        // Handle the button that shows/hides the help section.
        const helpBtn = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_HELP_VISIBILITY);
        if (helpBtn) {
            helpBtn.addEventListener("click", MxnSearchUiHandler.ToggleShowHelp);
        }

        // Handle the button to toggle the search join (AND/OR).
        const joinBtn = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_JOIN);
        if (joinBtn) {
            joinBtn.addEventListener("click", MxnSearchUiHandler.ToggleSearchJoin);
            joinBtn.addEventListener("click",  MxnSearchHandler.SearchAndOutput);
        }

        // Handle the button to toggle the search fuzzy in the results.
        const fuzzyBtn = document.getElementById(MxnSearchUiHandler.ID_BTN_SEARCH_FUZZY);
        if (fuzzyBtn) {
            fuzzyBtn.addEventListener("click", MxnSearchUiHandler.ToggleSearchFuzzy);
            fuzzyBtn.addEventListener("click",  MxnSearchHandler.SearchAndOutput);
        }

        // Handle the button to toggle the sorting in the results.
        const sortingBtn = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_SORTING);
        if (sortingBtn) {
            sortingBtn.addEventListener("click", MxnSearchUiHandler.ToggleResultSorting);
            sortingBtn.addEventListener("click",  MxnSearchHandler.SearchAndOutput);
        }

        // Handle the button to toggle the verbosity in the results.
        const verbosityBtn = document.getElementById(MxnSearchUiHandler.ID_BTN_RESULT_VERBOSITY);
        if (verbosityBtn) {
            verbosityBtn.addEventListener("click", MxnSearchUiHandler.SetOrToggleResultVerbosity);
            verbosityBtn.addEventListener("click",  MxnSearchHandler.SearchAndOutput);
        }

        // Handle the search field input to trigger live search updates.
        const searchInput = document.querySelector(
            `#${MxnSearchUiHandler.ID_SEARCH_FORM} input[name="${MxnSearchUiHandler.QUERY_VALUE}"]`);
        if (searchInput) {
            searchInput.addEventListener("input", MxnSearchHandler.SearchAndOutput);
        }

        // Handle the form submission to build the search URL.
        const form = document.getElementById(MxnSearchUiHandler.ID_SEARCH_FORM);
        if (form) {
            form.addEventListener("submit", MxnSearchUiHandler.OnSubmitSearchForm);
        }
    }
}


class MxnSearchHandler {

    /* Returns the relative root URL for this page. */
    static GetRoot() {
        const searchInput = document.getElementById(MxnSearchUiHandler.ID_SEARCH_BAR_TOP);
        const attribute = searchInput ? searchInput.getAttribute("data-target") : null;
        if (!attribute) 
            return "#";

        const slashIndex = attribute.lastIndexOf("/");
        return slashIndex !== -1 ? attribute.substring(0, slashIndex + 1) : "";
    }

    /* Validates that the search data is properly defined. */
    static ValidateData() {

        const keys = Object.keys(MXN_SEARCH_DATA.fields || {});
        if (!keys.includes("uri") || !keys.includes("domain") || !keys.includes("entity") ||
            !keys.includes("context") || !keys.includes("name") || !keys.includes("signature") ||
            !keys.includes("description") || !keys.includes("value") || !keys.includes("owner") ||
            !keys.includes("weight") || !keys.includes("pid")) {
            console.error("Search fields are not properly defined.");
            return;
        }
    }

    /* Extracts a snippet around #match within #value.
       
       #Distance is the number of characters to include before and after the match. Will stop early
       at double line breaks, i.e., when thre is a double line break, it will cut off there, even
       if the distance is not yet reached.
    */
    static ExtractSnippet(item, match, maxDistance) {

        if (!item || !item.value) return "";

        // There is no match, return start of the value up to distance * 2. For API items with
        // signatures, we do not return anything.
        if(!match) 
            return (item.signature ? "" : 
                    item.value.substring(0, maxDistance * 2) + (item.value.length > maxDistance * 2 ? " ..." : ""));

        // This some kind of larger text match, we try to extract a snippet around it.
        const value = item.value;
        const msi = match.index; // Match start index
        const mei = msi + match[0].length; // Match end index

        // Find the first double line break BEFORE the match
        let lba = value.lastIndexOf("\n\n", msi);
        if (lba === -1) lba = 0; // No double line break found, fallback to start of the string

        // Find the first double line break AFTER the match
        let lbb = value.indexOf("\n\n", mei);
        if (lbb === -1) lbb = value.length; // No double line break found, fallback to end of the string

        // Calculate the snippet boundaries
        const a = lba > 0 && msi - lba > maxDistance ? msi - maxDistance : lba;
        const b = lbb > 0 && lbb - mei < maxDistance ? lbb : mei + maxDistance;

        // Extract the snippet and add ellipses if truncated
        const prefix = a > 0 ? "... " : "";
        const suffix = b < value.length ? " ..." : "";
        const result = prefix + value.substring(a, b).trim() + suffix;
        
        return result;
    }

    /* Returns #text as a preformatted block wrapped in a paragraph. */
    static AsPreformattedResult(text, extraClasses = []) {

        let p = document.createElement("p");
        let pre = document.createElement("pre");
        p.classList.add(...extraClasses);
        pre.innerHTML = text || "No description";
        p.appendChild(pre);
        return p;
    }
    
    /* Builds the search results HTML and outputs it to the results container. */
    static Output(results) {
        
        const isVerbose = MxnSearchUiHandler.IsVerboseMode();
        let info = document.getElementById(MxnSearchUiHandler.ID_SEARCH_INFO);
        let container = document.getElementById(MxnSearchUiHandler.ID_SEARCH_RESULTS);
        if (!info || !container || !results) return;
    
        // Build the results.
        MxnSearchUiHandler.ClearResults(results.length);
        results.forEach(function (item) {
    
            let classification = MxnSearchUiHandler.MAP_ENTITY_VALUE_TO_LABEL[item.entity] || "Unknown";
            let prefix = MxnSearchUiHandler.MAP_ENTITY_VALUE_TO_PREFIX[item.entity] || "?";
            let help = classification !== "?" ? `${classification} match` : "Unknown match";
            
            // Build the layout.
            let a = document.createElement("a");
            a.classList.add("mxn-result");
            a.href = item.uri || "#";
            a.setAttribute("title", help);
            container.appendChild(a);
    
            let content = document.createElement("div");
            content.classList.add("mxn-content");
            a.appendChild(content);
    
            let match = document.createElement("div");
            match.classList.add("mxn-classification");
    
            match.textContent = prefix;
            content.appendChild(match);
    
            let context = document.createElement("div");
            context.classList.add("mxn-context");
            content.appendChild(context);
            
            // Add the pirmary content.
            if (item.signature) {
                context.appendChild(
                    MxnSearchHandler.AsPreformattedResult(item.signature, ["mxn-code-result", "mxn-signature"]));
                if (isVerbose) {
                    context.appendChild(MxnSearchHandler.AsPreformattedResult(
                        item.description, ["mxn-text-result", "mxn-description", "mxn-secondary"]));
                }
            }
            if (item.value && (isVerbose || !item.signature)) {
                context.appendChild(MxnSearchHandler.AsPreformattedResult(item.value, 
                    [
                        item.context & MxnSearchUiHandler.VAL_CODE ? "mxn-code-result" : "mxn-text-result", 
                        "mxn-value", 
                        item.signature ? "mxn-secondary" : "mxn-primary"
                    ]));
            }
            
            // Add the tags footer.
            if (isVerbose) {
                let tags = document.createElement("div");
                tags.classList.add("mxn-tags");
                context.appendChild(tags);

                let page = document.createElement("span");
                page.classList.add("mxn-owner");
                page.textContent = item.owner || "Unknown owner";
                tags.appendChild(page);
                (item.tags || []).forEach(function (tag) {
                    let span = document.createElement("span");
                    span.textContent = tag;
                    tags.appendChild(span);
                });
            }

            // Add the separator between results.
            let separator = document.createElement("div");
            separator.classList.add("mxn-separator");
            container.appendChild(separator);
        });
    }

    /* Processes the raw search results from the search index and builds the final result set. */
    static Process(results, sortByClassification) {

        // Build the basic data.
        const baseUri = MxnSearchHandler.GetRoot();
        const isVerbose = MxnSearchUiHandler.IsVerboseMode(); 
        let data = [];

        results.forEach(function (item) {

            let context = item.context || 0;
            let matchValues = Object.values(item.match).flat();
            if (matchValues.includes("name")) context = MxnSearchUiHandler.VAL_NAME;
            else if (matchValues.includes("signature")) context = MxnSearchUiHandler.VAL_SIGNATURE;
            else if (matchValues.includes("description")) context = MxnSearchUiHandler.VAL_TEXT;
            else if (matchValues.includes("value") && item.signature) context = MxnSearchUiHandler.VAL_TEXT;

            data.push({
                context: context,
                description: item.description || "",
                domain: item.domain || 0,
                entity: item.entity || 0,
                match: matchValues,
                name: item.name || "",
                owner: item.owner || "",
                pid: item.pid|| 0,
                score: item.score * (item.weight || 1),
                signature: item.signature || "",
                terms: item.terms,
                uri: `${baseUri}${item.uri}` || "",
                value: item.value || "",
                tags: [
                    item.domain === MxnSearchUiHandler.VAL_API ? "API" : null,
                    item.domain === MxnSearchUiHandler.VAL_PAGES ? "Manual" : null,
                    item.domain === MxnSearchUiHandler.VAL_EXAMPLES ? "Example" : null,
                    item.entity === MxnSearchUiHandler.VAL_GENERIC ? "Page" : null,
                    item.entity === MxnSearchUiHandler.VAL_CLASS ? "Class" : null,
                    item.entity === MxnSearchUiHandler.VAL_METHOD ? "Method" : null,
                    item.entity === MxnSearchUiHandler.VAL_FUNCTION ? "Function" : null,
                    item.entity === MxnSearchUiHandler.VAL_ATTRIBUTE ? "Attribute" : null,
                    context === MxnSearchUiHandler.VAL_TEXT ? "Text" : null,
                    context === MxnSearchUiHandler.VAL_HEADING ? "Heading" : null,
                    context === MxnSearchUiHandler.VAL_CODE ? "Code" : null,
                    context === MxnSearchUiHandler.VAL_NAME ? "Name" : null,
                    context === MxnSearchUiHandler.VAL_SIGNATURE ? "Signature" : null,
                    context === MxnSearchUiHandler.VAL_METADATA ? "Metadata" : null
                ].filter(Boolean)
            });

        });

        // Compress the data, i.e., join items that only differ by context or the matched term
        // but are otherwise for the same entity.
        for (let i = 0; i < data.length; i++) {
            for (let j = i + 1; j < data.length; j++) {
                if (data[i].pid === data[j].pid && data[i].value === data[j].value &&
                    data[i].signature === data[j].signature && data[i].owner === data[j].owner &&
                    data[i].name === data[j].name && data[i].domain === data[j].domain &&
                    data[i].entity === data[j].entity) {

                    // Merge contexts into tags.
                    let contextTag = null;
                    if (data[j].context === MxnSearchUiHandler.VAL_TEXT) contextTag = "Text";
                    else if (data[j].context === MxnSearchUiHandler.VAL_HEADING) contextTag = "Heading";
                    else if (data[j].context === MxnSearchUiHandler.VAL_CODE) contextTag = "Code";
                    else if (data[j].context === MxnSearchUiHandler.VAL_NAME) contextTag = "Name";
                    else if (data[j].context === MxnSearchUiHandler.VAL_SIGNATURE) contextTag = "Signature";
                    else if (data[j].context === MxnSearchUiHandler.VAL_METADATA) contextTag = "Metadata";
                    if (contextTag && !data[i].tags.includes(contextTag)) data[i].tags.push(contextTag);

                    // Merge match fields, logarithmically sum the scores, and remove the duplicate.
                    data[i].match = Array.from(new Set(data[i].match.concat(data[j].match)));
                    data[i].score = Math.log(Math.exp(data[i].score) + Math.exp(data[j].score));
                    data.splice(j, 1);
                    j--;
                }
            }
        }

        // Highlight the matched terms name, signature, description, or value. Also clamp value fields to 
        // the first 100 characters before and after the first match or 200 characters total when there is no match.
        data.forEach(function (item) {

            let terms = item.terms || [];
            let termsRegex = new RegExp(
                `(${terms.map(t => t.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')).join("|")})`, "gi");

            // Highlight matches in name, signature, description.
            if (item.name) {
                item.name = item.name.replace(termsRegex, '<mark>$1</mark>');
            }
            if (item.signature) {
                item.signature = item.signature.replace(termsRegex, '<mark>$1</mark>');
            }
            if (item.description) {
                item.description = item.description.replace(termsRegex, '<mark>$1</mark>');
            }
            // Highlight matches in the value, i.e., whole context of the item.
            if (item.value) {
                item.value = MxnSearchHandler.ExtractSnippet(
                    item, termsRegex.exec(item.value), 
                    isVerbose ? MxnSearchUiHandler.SNIPPET_DISTANCE_VERBOSE : 
                                MxnSearchUiHandler.SNIPPET_DISTANCE_COMPACT);

                if (item.value) {
                    item.value = item.value.replace(termsRegex, '<mark>$1</mark>');
                }
            }
        });
        
        // Sort the data either by entity and score or just by score.
        if (sortByClassification) {
            data = data.sort((a, b) => {
                if (a.entity !== b.entity) return a.entity - b.entity;
                return b.score - a.score;
            });
        }
        else {
            data = data.sort((a, b) => b.score - a.score);
        }
        
        return data;
    }

    /* Performs the search based on the current settings and returns the results. */
    static Search() {

        let form = document.getElementById(MxnSearchUiHandler.ID_SEARCH_FORM);
        if (!form) {
            console.error("Search form not found.");
            return;
        }

        const query = (form.querySelector(`input[name="${MxnSearchUiHandler.QUERY_VALUE}"]`).value || "").trim();
        if (!query) return [];

        const settings = JSON.parse(localStorage.getItem(MxnSearchUiHandler.NME_STORAGE)) || {};
        const modes = settings.modes || 0;
        const domains = settings.domains || 0;
        const entities = settings.entities || 0;
        const contexts = settings.contexts || 0;
        const joinWithAnd = (modes & MxnSearchUiHandler.VAL_SEARCH_JOIN_AND) !== 0;
        const fuzzySearch = (modes & MxnSearchUiHandler.VAL_SEARCH_FUZZY) !== 0;
        const sortByClassification = (modes & MxnSearchUiHandler.VAL_SEARCH_SORT_CLASSIFICATION) !== 0;

        // Initialize the search engine, add all documents, and perform the search.
        let engine = new MiniSearch({
            fields: ["name", "signature", "description", "value"],
            storeFields: ["id", "uri", "domain", "entity", "context", "name", "signature",
                          "description", "value", "owner", "pid", "weight"],
        });
        engine.addAll(MXN_SEARCH_DATA.documents);
    
        // Define the search based on the current settings and if the query contains quoted phrases.
        const isQuotedQuery = /["']([^"']+)["']/.test(query);
        const isFuzzySearch = fuzzySearch && !isQuotedQuery;

        // Tests if the document matches the selected facets.
        let isFacetMatch = function(doc) {
            if (((doc["domain"] & domains) === 0) || ((doc["entity"] & entities) === 0) || 
                ((doc["context"] & contexts) === 0))
                return false;

            return true;
        }
            
        let searchOptions = {
            filter: isFacetMatch,
            expand: isFuzzySearch,  
            prefix: isFuzzySearch,
            fuzzy: isFuzzySearch ? (term => term.length > 3 ? 0.2 : null) : null,
            combineWith: joinWithAnd ? 'AND' : 'OR',
        };

        // If we have a quoted phrase, extract it and search for exact matches
        let queryToSearch = query;
        if (isQuotedQuery) {
            // Extract quoted content and non-quoted terms
            let quotedPhrases = [];
            let remainingQuery = query;
    
            // Extract all quoted phrases
            remainingQuery = remainingQuery.replace(/["']([^"']+)["']/g, (match, phrase) => {
                quotedPhrases.push(phrase);
                return '';
            });
    
            // If we have quoted phrases, use combineWith: 'AND' for stricter matching
            searchOptions.combineWith = 'AND';
    
            // For exact phrase matching, we'll modify the query to be more restrictive
            if (quotedPhrases.length > 0) {
                // Create a modified query that searches for the exact phrase
                queryToSearch = quotedPhrases.join(' ') + ' ' + remainingQuery.trim();
                queryToSearch = queryToSearch.trim();
            }
        }
        
        // Post-filter for exact phrase matching if we have quoted phrases
        let results = engine.search(queryToSearch, searchOptions);
        if (isQuotedQuery) {
            const quotedPhrases = [];
            query.replace(/["']([^"']+)["']/g, (match, phrase) => {
                quotedPhrases.push(phrase.toLowerCase());
                return '';
            });
    
            if (quotedPhrases.length > 0) {
                results = results.filter(result => {
                    const doc = MXN_SEARCH_DATA.documents[result.id];
                    const searchableText = [
                        doc.name || '',
                        doc.signature || '',
                        doc.description || '',
                        doc.value || ''
                    ].join(' ').toLowerCase();
    
                    // Check if all quoted phrases exist in the document
                    return quotedPhrases.every(phrase => searchableText.includes(phrase));
                });
            }
        }
    
        return MxnSearchHandler.Process(results, sortByClassification);
    }

    /* Performs the search and outputs the results. */
    static SearchAndOutput() {
        const results = MxnSearchHandler.Search();
        MxnSearchUiHandler.ClearResults(results.length);
        MxnSearchHandler.Output(results);
    }
}

// --- Attach ----------------------------------------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", function () {

    MxnSearchHandler.ValidateData(); // Make sure the search index is valid data.
    MxnSearchUiHandler.Attach();  // Attach the handler for the search UI.
    
    // Either run the first search on the search page or attach the global keyboard handler for all other pages.
    if (MxnSearchUiHandler.IsMainSearchPage()) {
        MxnSearchHandler.SearchAndOutput();
        MxnSearchUiHandler.FocusSearchInput();
    } else {
        document.addEventListener("keydown", MxnSearchUiHandler.OnKeyboardEvent);
        MxnSearchUiHandler.SetOrToggleResultVerbosity(null, MxnSearchUiHandler.CLS_RESULT_COMPACT);
    }
});