/* Vortex Core JS - Premium UI Interactions */

const Vortex = {
    toast: function(message, type = 'info', title = '') {
        const container = document.getElementById('vortex-toast-container');
        if (!container) {
            const newContainer = document.createElement('div');
            newContainer.id = 'vortex-toast-container';
            document.body.appendChild(newContainer);
        }
        
        const toast = document.createElement('div');
        toast.className = `vortex-toast toast-${type}`;
        
        let icon = 'fa-info-circle';
        if (type === 'success') icon = 'fa-check-circle';
        if (type === 'danger') icon = 'fa-exclamation-triangle';
        
        if (!title) {
            title = type.charAt(0).toUpperCase() + type.slice(1);
            if (type === 'success') title = 'Başarılı';
            if (type === 'danger') title = 'Hata';
        }

        toast.innerHTML = `
            <div class="vortex-toast-icon">
                <i class="fas ${icon}"></i>
            </div>
            <div class="vortex-toast-content">
                <div class="vortex-toast-title">${title}</div>
                <div class="vortex-toast-msg">${message}</div>
            </div>
        `;

        document.getElementById('vortex-toast-container').appendChild(toast);

        const removeToast = () => {
            toast.classList.add('hiding');
            setTimeout(() => toast.remove(), 400);
        };

        toast.onclick = removeToast;
        setTimeout(removeToast, 5000);
    },

    initPageAnimations: function() {
        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            el.classList.add('animate-fade-in');
        });
    }
};

// Global Initialization
document.addEventListener('DOMContentLoaded', () => {
    Vortex.initPageAnimations();
});
