document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('contact-form').addEventListener('submit', function(event) {
        event.preventDefault();
        alert('Message sent!');
    });

    document.getElementById('registration-form').addEventListener('submit', function(event) {
        event.preventDefault();
        alert('Registration successful!');
    });

    // Bouncing animation for the footer
    const footer = document.querySelector('footer');
    footer.style.position = 'relative';
    let position = 0;
    let direction = 1;

    function bounce() {
        position += direction;
        footer.style.bottom = `${position}px`;

        if (position >= 20 || position <= 0) {
            direction *= -1;
        }

        requestAnimationFrame(bounce);
    }

    bounce();
});