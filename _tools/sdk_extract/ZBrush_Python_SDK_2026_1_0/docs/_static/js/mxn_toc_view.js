/* Contains the logic for the collapsible TOC in the sidebar. */

document.addEventListener("DOMContentLoaded", function() {
    /// Determines if a list item should be opened by default when the page loads or when restoring
    /// the default collapsed state.
    function isDefaultOpen(li, defaultDepth, defaultClosed) {
        var level = 0;
        var el = li;
        while (el && el.parentElement) {
            if (el.parentElement.tagName.toLowerCase() === "ul") level++;
            el = el.parentElement.parentElement;
            if (el && el.classList && el.classList.contains("foldable-toc")) break;
        }

        var label = "";
        var toggle = li.querySelector(".toggle");
        if (toggle) {
            var anchor = toggle.querySelector("a");
            if (anchor) label = anchor.textContent.trim();
        }
        if (defaultClosed && defaultClosed.includes(label)) return false;
        return level <= defaultDepth;
    }

    // Get the toggle defaults from the data attributes.
    function getSettings() {
        var toc = document.querySelector(".mxn-toc-view");
        var defaultDepth = toc ? parseInt(toc.dataset.defaultDepth, 10) : 0;
        var defaultClosed = [];
        if (toc && toc.dataset.defaultClosed && toc.dataset.defaultClosed !== "undefined") {
            try {
                defaultClosed = JSON.parse(toc.dataset.defaultClosed);
            } catch (e) {
                defaultClosed = [];
            }
        }
        var allNested = toc ? toc.querySelectorAll("li.nested") : [];
        var expander = document.querySelector(".mxn-toc-view .expander");
        return {toc, defaultDepth, defaultClosed, allNested, expander};
    }

    // Add click listener to the toggle area (excluding the link itself).
    document.querySelectorAll(".mxn-toc-view .toggle").forEach(function(area) {
        area.addEventListener("click", function(e) {
            if (e.target.tagName.toLowerCase() === "a") return;
            var li = area.parentElement;
            li.classList.toggle("open");
        });
    });

    // Get the toggle defaults from the data attributes.
    var toc = document.querySelector(".mxn-toc-view");
    var defaultDepth = toc ? parseInt(toc.dataset.defaultdepth, 10) : 0;
    var defaultClosed = [];
    if (toc && toc.dataset.defaultclosed && toc.dataset.defaultclosed !== "undefined") {
        try {
            defaultClosed = JSON.parse(toc.dataset.defaultclosed);
        } catch (e) {
            defaultClosed = [];
        }
    }
    var allNested = toc ? toc.querySelectorAll("li.nested") : [];
    var expander = document.querySelector(".mxn-toc-view .expander");

    // Set the initial state of the TOC based on the defaults.
    if (toc) {
        allNested.forEach(function(li) {
            if (isDefaultOpen(li, defaultDepth, defaultClosed)) {
                li.classList.add("open");
            } else {
                li.classList.remove("open");
            }
        });
    }

    // Expander button logic
    if (expander) {
        expander.addEventListener("click", function() {
            // Button is in "expand all" state
            if (expander.classList.contains("bi-arrows-expand")) {
    
                allNested.forEach(function(li) {
                    li.classList.add("open");
                });
                expander.classList.remove("bi-arrows-expand");
                expander.classList.add("bi-arrows-collapse");
            // Button is in "collapse all" state
            } else {
                allNested.forEach(function(li) {
                    if (isDefaultOpen(li, defaultDepth, defaultClosed)) {
                        li.classList.add("open");
                    } else {
                        li.classList.remove("open");
                    }
                });
                expander.classList.remove("bi-arrows-collapse");
                expander.classList.add("bi-arrows-expand");
            }
        });
    }
});