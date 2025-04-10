document.addEventListener('DOMContentLoaded', function() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const progressSection = document.getElementById('progress');
    const statusText = document.getElementById('status-text');
    const errorDiv = document.getElementById('error');
    const apiKeyInput = document.getElementById('api-key');
    const selectedFileDiv = document.getElementById('selected-file');
    const fileNameSpan = document.getElementById('file-name');
    const processButton = document.getElementById('process-button');
    const useMockCheckbox = document.getElementById('use-mock');
    
    let selectedFile = null;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

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

    uploadZone.addEventListener('drop', handleDrop, false);
    uploadZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    processButton.addEventListener('click', () => {
        if (useMockCheckbox && useMockCheckbox.checked) {
            processFile(selectedFile);
        } else if (selectedFile) {
            processFile(selectedFile);
        }
    });

    if (selectedFileDiv) {
        selectedFileDiv.querySelector('.btn-close').addEventListener('click', () => {
            resetFileSelection();
        });
    }

    if (useMockCheckbox) {
        useMockCheckbox.addEventListener('change', () => {
            processButton.style.display = useMockCheckbox.checked ? 'inline-block' : (selectedFile ? 'inline-block' : 'none');
            uploadZone.style.display = selectedFile ? 'none' : 'block';
            selectedFileDiv.style.display = selectedFile ? 'block' : 'none';
        });
    }

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

        const extension = file.name.split('.').pop().toLowerCase();
        if (!['zip', 'json', 'xml'].includes(extension)) {
            showError('Invalid file type. Please upload a ZIP, JSON, or XML file.');
            return;
        }

        if (file.size > 100 * 1024 * 1024) {
            showError('File is too large. Maximum size is 100MB.');
            return;
        }

        selectedFile = file;
        fileNameSpan.textContent = file.name;
        selectedFileDiv.style.display = 'block';
        processButton.style.display = 'inline-block';
        uploadZone.style.display = 'none';
        errorDiv.style.display = 'none';
    }

    function resetFileSelection() {
        selectedFile = null;
        fileInput.value = '';
        selectedFileDiv.style.display = 'none';
        processButton.style.display = useMockCheckbox && useMockCheckbox.checked ? 'inline-block' : 'none';
        uploadZone.style.display = 'block';
        errorDiv.style.display = 'none';
    }

    function processFile(file) {
        if (!useMockCheckbox?.checked && apiKeyInput && !apiKeyInput.value.trim()) {
            showError('Please enter your API key.');
            return;
        }

        errorDiv.style.display = 'none';
        progressSection.style.display = 'block';
        selectedFileDiv.style.display = 'none';
        processButton.style.display = 'none';
        uploadZone.style.display = 'none';
        if (useMockCheckbox) {
            useMockCheckbox.disabled = true;
        }
        statusText.textContent = 'Uploading file...';

        const formData = new FormData();
        if (file) {
            formData.append('file', file);
        }
        if (apiKeyInput) {
            formData.append('api_key', apiKeyInput.value.trim());
        }
        if (useMockCheckbox) {
            formData.append('use_mock', useMockCheckbox.checked);
        }

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
        if (useMockCheckbox) {
            useMockCheckbox.disabled = false;
        }
        
        uploadZone.style.display = selectedFile ? 'none' : 'block';
        selectedFileDiv.style.display = selectedFile ? 'block' : 'none';
        processButton.style.display = (useMockCheckbox?.checked || selectedFile) ? 'inline-block' : 'none';
    }
});