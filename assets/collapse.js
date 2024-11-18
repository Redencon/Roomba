document.addEventListener("DOMContentLoaded", function() {
    var interval = setInterval(function() {
        var collapsibleButtons = document.querySelectorAll('[data-bs-toggle="collapse"]');
        
        if (collapsibleButtons.length > 0) {
            clearInterval(interval);
            console.log('Collapsible buttons found:', collapsibleButtons);
            
            collapsibleButtons.forEach(function(button) {
                button.addEventListener('click', function() {
                    console.log('Collapsible button clicked:', button);
                    var targetSelector = button.getAttribute('data-bs-target');
                    var targetElement = document.querySelector(targetSelector);
                    
                    if (targetElement) {
                        targetElement.collapse('toggle');
                    }
                });
            });
        } else {
            console.log('No collapsible buttons found');
        }
    }, 100); // Check every 100 milliseconds
});