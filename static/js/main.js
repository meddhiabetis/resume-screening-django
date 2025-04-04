// Add your JavaScript code here
document.addEventListener('DOMContentLoaded', function() {
    // Handle search type changes
    const searchTypeSelect = document.getElementById('search-type');
    if (searchTypeSelect) {
        searchTypeSelect.addEventListener('change', function() {
            document.querySelector('form').submit();
        });
    }

    // Handle file upload progress
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            // Show upload progress
            const progressDiv = document.createElement('div');
            progressDiv.className = 'upload-progress';
            progressDiv.innerHTML = 'Uploading files...';
            this.parentNode.appendChild(progressDiv);
        });
    }
});