/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         Notification system
 * ======================================================================= */

class NotificationSystem {
    constructor() {
        this.container = document.createElement('div');
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `notification notification-${type}`;

        const icon = this._getIcon(type);

        toast.innerHTML = `
            <span class="notification-icon">${icon}</span>
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;

        this.container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Close button
        toast.querySelector('.notification-close').addEventListener('click', () => {
            this.dismiss(toast);
        });

        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => {
                this.dismiss(toast);
            }, duration);
        }
    }

    dismiss(toast) {
        toast.classList.remove('show');

        const removeToast = () => {
            toast.remove();
            toast.removeEventListener('transitionend', removeToast);
        };

        toast.addEventListener('transitionend', removeToast);

        // Fallback in case transition doesn't fire
        setTimeout(removeToast, 500);
    }

    _getIcon(type) {
        switch (type) {
            case 'success': return '✅';
            case 'error': return '❌';
            case 'warning': return '⚠️';
            default: return 'ℹ️';
        }
    }

    success(message) { this.show(message, 'success'); }
    error(message) { this.show(message, 'error'); }
    warning(message) { this.show(message, 'warning'); }
    info(message) { this.show(message, 'info'); }
}

window.notifications = new NotificationSystem();

// Global helper for compatibility
window.showNotification = (message, type) => {
    window.notifications.show(message, type);
};
