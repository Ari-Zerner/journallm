document.addEventListener('DOMContentLoaded', function() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const progressSection = document.getElementById('progress');
    const statusText = document.getElementById('status-text');
    const errorDiv = document.getElementById('error');

    // Handle drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Handle drag and drop visual feedback
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        uploadZone.classList.add('dragover');
    }

    function unhighlight() {
        uploadZone.classList.remove('dragover');
    }

    // Handle file drop
    uploadZone.addEventListener('drop', handleDrop, false);
    uploadZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        handleFile(file);
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        handleFile(file);
    }

    function handleFile(file) {
        if (!file) return;

        // Check file type
        const extension = file.name.split('.').pop().toLowerCase();
        if (!['zip', 'json', 'xml'].includes(extension)) {
            showError('Invalid file type. Please upload a ZIP, JSON, or XML file.');
            return;
        }

        // Check file size (100MB limit)
        if (file.size > 100 * 1024 * 1024) {
            showError('File is too large. Maximum size is 100MB.');
            return;
        }

        uploadFile(file);
    }

    function uploadFile(file) {
        // Reset state
        errorDiv.style.display = 'none';
        progressSection.style.display = 'block';
        uploadZone.style.display = 'none';
        statusText.textContent = 'Uploading file...';

        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            pollStatus(data.job_id);
        })
        .catch(error => {
            showError(error.message || 'Error uploading file');
        });
    }

    function pollStatus(jobId) {
        statusText.textContent = 'Processing your journal...';

        const poll = () => {
            fetch(`/status/${jobId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }

                    switch (data.status) {
                        case 'complete':
                            if (data.redirect) {
                                window.location.href = data.redirect;
                            }
                            break;
                        case 'error':
                            throw new Error(data.error || 'Processing failed');
                        case 'processing':
                        case 'starting':
                            setTimeout(poll, 2000);
                            break;
                    }
                })
                .catch(error => {
                    showError(error.message || 'Error checking status');
                });
        };

        poll();
    }

    function showError(message) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        progressSection.style.display = 'none';
        uploadZone.style.display = 'block';
        fileInput.value = '';
    }
});