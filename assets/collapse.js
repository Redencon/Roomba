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
document.addEventListener("DOMContentLoaded", function() {
    var interval = setInterval(function() {
        var go_top_button = document.getElementById("go-top-button");
        if (go_top_button) {
            clearInterval(interval);
            console.log('Go top button found:', go_top_button);
            go_top_button.addEventListener("click", function() {
                document.getElementById("main_header").scrollIntoView({ behavior: 'smooth' });});
        }
    },100);
});