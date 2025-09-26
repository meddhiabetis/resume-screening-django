class DashboardManager {
    constructor() {
        // Cache elements
        this.uploadSection = document.querySelector('.upload-section') || document.getElementById('uploadCollapse');
        this.toggleButton = document.getElementById('toggleUpload');
        this.closeButton = document.getElementById('closeUpload');
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('fileInput');
        this.fileList = document.getElementById('fileList');
        this.uploadButton = document.getElementById('uploadButton');
        this.uploadForm = document.getElementById('uploadForm');
        this.progressBar = document.querySelector('#uploadProgress .progress-bar');
        this.progressText = document.querySelector('#uploadProgress .progress-text');
        this.uploadProgress = document.getElementById('uploadProgress');

        this.files = new Set();

        // Prevent double-binding if script is loaded twice
        if (window.__dashboardManagerListenersAttached) return;
        this._dialogJustOpened = false;
        this.initializeEventListeners();
        window.__dashboardManagerListenersAttached = true;
    }

    initializeEventListeners() {
        // Toggle upload section (if present)
        if (this.toggleButton && this.uploadSection) {
            this.toggleButton.addEventListener('click', () => this.toggleUploadSection());
        }
        if (this.closeButton && this.uploadSection) {
            this.closeButton.addEventListener('click', () => this.closeUploadSection());
        }

        // File drag & drop
        if (this.dropZone) {
            this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
            this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            this.dropZone.addEventListener('drop', (e) => this.handleDrop(e));

            // IMPORTANT: Avoid double-opening the file dialog.
            // Ignore clicks that originate from the "Select Files" button inside the drop zone,
            // because that button already has an inline onclick that triggers fileInput.click().
            this.dropZone.addEventListener('click', (e) => {
                if (!this.fileInput) return;

                // If the click came from a button inside the drop zone, let the button's own handler run.
                const clickedButton = e.target.closest('button');
                if (clickedButton) return;

                // Re-entrancy guard: if another handler already triggered a dialog, skip
                if (this._dialogJustOpened) return;

                this._dialogJustOpened = true;
                this.fileInput.click();

                // Release guard after a short delay to swallow any duplicate queued clicks
                setTimeout(() => {
                    this._dialogJustOpened = false;
                }, 350);
            });
        }

        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        // Form submission
        if (this.uploadForm) {
            this.uploadForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Initialize table scroll (safe if not present)
        this.initializeTableScroll();
    }

    toggleUploadSection() {
        if (!this.uploadSection) return;
        const isCollapsed = this.uploadSection.classList?.contains('collapse');
        if (isCollapsed) {
            // If using Bootstrap collapse component
            this.uploadSection.classList.add('show');
        } else {
            // Fallback display toggle
            if (this.uploadSection.style.display === 'none' || this.uploadSection.style.display === '') {
                this.uploadSection.style.display = 'block';
                this.uploadSection.classList?.add('show');
            } else {
                this.closeUploadSection();
            }
        }
    }

    closeUploadSection() {
        if (!this.uploadSection) return;
        const isCollapsed = this.uploadSection.classList?.contains('collapse');
        if (isCollapsed) {
            this.uploadSection.classList.remove('show');
        } else {
            this.uploadSection.classList?.remove('show');
            setTimeout(() => {
                this.uploadSection.style.display = 'none';
            }, 300);
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        if (this.dropZone) this.dropZone.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        if (this.dropZone) this.dropZone.classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        if (this.dropZone) this.dropZone.classList.remove('drag-over');
        if (e.dataTransfer?.files) {
            this.handleFiles(e.dataTransfer.files);
        }
    }

    handleFileSelect(e) {
        if (e.target?.files) {
            this.handleFiles(e.target.files);
        }
    }

    handleFiles(fileList) {
        if (!fileList) return;
        for (let file of fileList) {
            if (this.isValidFileType(file)) {
                this.files.add(file);
            }
        }
        this.updateFileList();
    }

    isValidFileType(file) {
        const validTypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];
        // Also accept PDFs where type may be blank
        return validTypes.includes(file.type) || file.name.toLowerCase().endsWith('.pdf');
    }

    updateFileList() {
        if (!this.fileList) return;
        this.fileList.innerHTML = '';
        this.files.forEach(file => {
            const fileItem = this.createFileItem(file);
            this.fileList.appendChild(fileItem);
        });
        if (this.uploadButton) {
            this.uploadButton.classList.toggle('d-none', this.files.size === 0);
        }
    }

    createFileItem(file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <i class="bi ${this.getFileIcon(file.name)} file-icon"></i>
                <div>
                    <div class="fw-medium">${file.name}</div>
                    <small class="text-muted">${this.formatFileSize(file.size)}</small>
                </div>
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger remove-file">
                <i class="bi bi-x"></i>
            </button>
        `;
        const removeBtn = fileItem.querySelector('.remove-file');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                this.files.delete(file);
                this.updateFileList();
            });
        }
        return fileItem;
    }

    getFileIcon(fileName) {
        const ext = fileName.split('.').pop().toLowerCase();
        const icons = {
            'pdf': 'bi-file-pdf text-danger',
            'doc': 'bi-file-word text-primary',
            'docx': 'bi-file-word text-primary'
        };
        return icons[ext] || 'bi-file-text text-secondary';
    }

    formatFileSize(bytes) {
        if (!Number.isFinite(bytes) || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        if (this.files.size === 0) return;

        const formData = new FormData();
        this.files.forEach(file => formData.append('resumes', file));

        const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrf) formData.append('csrfmiddlewaretoken', csrf.value);

        if (this.uploadProgress) this.uploadProgress.classList.remove('d-none');
        if (this.uploadButton) this.uploadButton.disabled = true;
        if (this.progressText) this.progressText.textContent = 'Uploading...';

        try {
            const response = await this.uploadFiles(formData);
            await this.handleUploadResponse(response);
        } catch (error) {
            this.handleUploadError(error);
        } finally {
            if (this.uploadButton) this.uploadButton.disabled = false;
            if (this.uploadProgress) this.uploadProgress.classList.add('d-none');
        }
    }

    async uploadFiles(formData) {
        const action = (this.uploadForm && this.uploadForm.getAttribute('action')) || window.location.href;
        return await fetch(action, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
    }

    async handleUploadResponse(response) {
        if (!response.ok) throw new Error('Upload failed (network/server error)');
        const result = await response.json();
        if (!result.success) throw new Error(result.error || 'Upload failed');

        this.showSuccessMessage(result.message || 'Upload complete');
        this.resetUploadForm();
        setTimeout(() => window.location.reload(), 1200);
    }

    handleUploadError(error) {
        alert('Error uploading files: ' + error.message);
    }

    showSuccessMessage(message) {
        const toast = document.createElement('div');
        toast.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 end-0 m-3';
        toast.style.zIndex = 2000;
        toast.innerHTML = `
            <strong>Success!</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    resetUploadForm() {
        this.files.clear();
        this.updateFileList();
        if (this.fileInput) this.fileInput.value = '';
        this.closeUploadSection();
    }

    initializeTableScroll() {
        const tableBody = document.querySelector('.table-responsive');
        if (!tableBody) return;
        const newUploads = document.querySelectorAll('.table-info');
        if (newUploads.length > 0) {
            const firstNewUpload = newUploads[0];
            const topPos = firstNewUpload.offsetTop - (tableBody.clientHeight / 2);
            tableBody.scrollTop = Math.max(0, topPos);
        }
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    try { new DashboardManager(); } catch (e) { console.warn('DashboardManager init skipped:', e); }
});