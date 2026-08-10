/* Contains the logic used by mxn-containers extensions. */

// Custom card clickable logic
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.mxn-card[data-uri]').forEach(function(card) {
    card.addEventListener('click', function() {
      window.location = card.getAttribute('data-uri');
    });
  });
});