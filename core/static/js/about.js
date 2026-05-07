document.addEventListener('DOMContentLoaded', function() {
    const dots = document.querySelectorAll('.timeline-dot');
    
    // Light RGB color palette
    const colors = [
        '#638c8d',
        '#3e91a2',
        '#0f3639',
        '#527e73',
        '#318a40',
        '#A0C4FF',
        '#BDB2FF',
        '#FFC6FF'

    ];

    dots.forEach((dot, i) => {
        let colorIndex = i % colors.length;
        dot.style.backgroundColor = colors[colorIndex];
        dot.style.animation = `pulse-${i} 2s infinite ${i * 200}ms`;

        // Force visible color transition even when CSS animation interpolation is inconsistent.
        setInterval(() => {
            colorIndex = (colorIndex + 1) % colors.length;
            dot.style.backgroundColor = colors[colorIndex];
        }, 450);

        const style = document.createElement('style');
        style.innerHTML = `
            @keyframes pulse-${i} {
                0%   { transform: scale(1);   background-color: ${colors[colorIndex % colors.length]}; }
                25%  { transform: scale(1.15); background-color: ${colors[(colorIndex + 1) % colors.length]}; }
                50%  { transform: scale(1.3);  background-color: ${colors[(colorIndex + 2) % colors.length]}; }
                75%  { transform: scale(1.15); background-color: ${colors[(colorIndex + 3) % colors.length]}; }
                100% { transform: scale(1);   background-color: ${colors[(colorIndex + 4) % colors.length]}; }
            }
        `;
        document.head.appendChild(style);
    });
});