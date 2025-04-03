class DashboardManager {
    constructor() {
        this.uploadSection = document.querySelector('.upload-section');
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

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Toggle upload section
        this.toggleButton.addEventListener('click', () => this.toggleUploadSection());
        this.closeButton.addEventListener('click', () => this.closeUploadSection());

        // File drag & drop
        this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e));
        this.dropZone.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Form submission
        this.uploadForm.addEventListener('submit', (e) => this.handleFormSubmit(e));

        // Initialize table scroll
        this.initializeTableScroll();
    }

    toggleUploadSection() {
        if (this.uploadSection.style.display === 'none') {
            this.uploadSection.style.display = 'block';
            this.uploadSection.classList.add('show');
        } else {
            this.closeUploadSection();
        }
    }

    closeUploadSection() {
        this.uploadSection.classList.remove('show');
        setTimeout(() => {
            this.uploadSection.style.display = 'none';
        }, 300);
    }

    handleDragOver(e) {
        e.preventDefault();
        this.dropZone.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.dropZone.classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        this.dropZone.classList.remove('drag-over');
        this.handleFiles(e.dataTransfer.files);
    }

    handleFileSelect(e) {
        this.handleFiles(e.target.files);
    }

    handleFiles(fileList) {
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
        return validTypes.includes(file.type);
    }

    updateFileList() {
        this.fileList.innerHTML = '';
        this.files.forEach(file => {
            const fileItem = this.createFileItem(file);
            this.fileList.appendChild(fileItem);
        });
        this.uploadButton.classList.toggle('d-none', this.files.size === 0);
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
        
        fileItem.querySelector('.remove-file').addEventListener('click', () => {
            this.files.delete(file);
            this.updateFileList();
        });
        
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
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        if (this.files.size === 0) return;

        const formData = new FormData();
        this.files.forEach(file => {
            formData.append('resumes', file);
        });

        formData.append(
            'csrfmiddlewaretoken',
            document.querySelector('[name=csrfmiddlewaretoken]').value
        );

        this.uploadProgress.classList.remove('d-none');
        this.uploadButton.disabled = true;

        try {
            const response = await this.uploadFiles(formData);
            await this.handleUploadResponse(response);
        } catch (error) {
            this.handleUploadError(error);
        } finally {
            this.uploadButton.disabled = false;
            this.uploadProgress.classList.add('d-none');
        }
    }

    async uploadFiles(formData) {
        return await fetch(this.uploadForm.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
    }

    async handleUploadResponse(response) {
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                this.showSuccessMessage(result.message);
                this.resetUploadForm();
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } else {
            throw new Error('Upload failed');
        }
    }

    handleUploadError(error) {
        alert('Error uploading files: ' + error.message);
    }

    showSuccessMessage(message) {
        const toast = document.createElement('div');
        toast.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 end-0 m-3';
        toast.innerHTML = `
            <strong>Success!</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(toast);
    }

    resetUploadForm() {
        this.files.clear();
        this.updateFileList();
        this.closeUploadSection();
    }

    initializeTableScroll() {
        const tableBody = document.querySelector('.table-responsive');
        const newUploads = document.querySelectorAll('.table-info');
        
        if (newUploads.length > 0) {
            const firstNewUpload = newUploads[0];
            const topPos = firstNewUpload.offsetTop - (tableBody.clientHeight / 2);
            tableBody.scrollTop = Math.max(0, topPos);
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DashboardManager();
});