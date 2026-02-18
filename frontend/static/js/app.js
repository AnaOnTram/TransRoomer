/**
 * TransRoomer - Frontend Application
 * Accessible, animated, and interactive
 */

(function() {
    'use strict';

    // Configuration
    // Use current host so it works whether accessed locally or from LAN
    const API_BASE_URL = window.location.origin;
    const FASTAPI_URL = window.location.origin;
    
    // State management
    const state = {
        currentFile: null,
        isGenerating: false,
        history: [],
        currentResult: null,
        iteration: 1,
        originalImagePath: null,  // Track original image for all iterations
        originalDescription: null  // Track original description
    };

    // DOM Elements
    const elements = {};

    /**
     * Initialize the application
     */
    function init() {
        cacheElements();
        setupEventListeners();
        setupTheme();
        loadHistory();
        announceToScreenReader('TransRoomer loaded');
    }

    /**
     * Cache DOM elements for performance
     */
    function cacheElements() {
        elements.dropZone = document.getElementById('drop-zone');
        elements.fileInput = document.getElementById('file-input');
        elements.previewContainer = document.getElementById('preview-container');
        elements.imagePreview = document.getElementById('image-preview');
        elements.removeImage = document.getElementById('remove-image');
        elements.description = document.getElementById('room-description');
        elements.resolution = document.getElementById('resolution');
        elements.resolutionValue = document.getElementById('resolution-value');
        elements.generateBtn = document.getElementById('generate-btn');
        elements.emptyState = document.getElementById('empty-state');
        elements.loadingState = document.getElementById('loading-state');
        elements.resultContent = document.getElementById('result-content');
        elements.expandBtn = document.getElementById('expand-btn');
        elements.resultStaged = document.getElementById('result-staged');
        elements.enhancedPrompt = document.getElementById('enhanced-prompt');
        elements.historyGrid = document.getElementById('history-grid');
        elements.themeToggle = document.getElementById('theme-toggle');
        elements.toastContainer = document.getElementById('toast-container');
        elements.downloadBtn = document.getElementById('download-btn');
        elements.newDesignBtn = document.getElementById('new-design-btn');
        elements.feedbackInput = document.getElementById('feedback-input');
        elements.refineBtn = document.getElementById('refine-btn');
        elements.iterationBadge = document.getElementById('iteration-badge');
    }

    /**
     * Setup all event listeners
     */
    function setupEventListeners() {
        // Drop zone events
        elements.dropZone.addEventListener('click', () => elements.fileInput.click());
        elements.dropZone.addEventListener('keydown', handleDropZoneKeydown);
        elements.dropZone.addEventListener('dragover', handleDragOver);
        elements.dropZone.addEventListener('dragleave', handleDragLeave);
        elements.dropZone.addEventListener('drop', handleDrop);
        
        // File input
        elements.fileInput.addEventListener('change', handleFileSelect);
        
        // Remove image
        elements.removeImage.addEventListener('click', removeImage);
        
        // Resolution slider
        elements.resolution.addEventListener('input', updateResolutionValue);
        
        // Description textarea
        elements.description.addEventListener('input', validateForm);
        
        // Generate button
        elements.generateBtn.addEventListener('click', generateDesign);
        
        // Theme toggle
        elements.themeToggle.addEventListener('click', toggleTheme);
        
        // Collapsible sections
        document.querySelectorAll('.collapsible').forEach(btn => {
            btn.addEventListener('click', toggleCollapsible);
        });
        
        // Result actions
        elements.downloadBtn.addEventListener('click', downloadResult);
        elements.newDesignBtn.addEventListener('click', resetForm);
        
        // Refine button
        if (elements.refineBtn) {
            elements.refineBtn.addEventListener('click', refineDesign);
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyboardShortcuts);
    }

    /**
     * Handle keyboard navigation for drop zone
     */
    function handleDropZoneKeydown(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            elements.fileInput.click();
        }
    }

    /**
     * Handle drag over
     */
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        elements.dropZone.classList.add('drag-over');
    }

    /**
     * Handle drag leave
     */
    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        elements.dropZone.classList.remove('drag-over');
    }

    /**
     * Handle file drop
     */
    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        elements.dropZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    }

    /**
     * Handle file selection
     */
    function handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    }

    /**
     * Process selected file
     */
    function handleFile(file) {
        // Validate file type
        if (!file.type.startsWith('image/')) {
            showToast('Please upload an image file', 'error');
            return;
        }
        
        // Validate file size (10MB max)
        if (file.size > 10 * 1024 * 1024) {
            showToast('File size must be less than 10MB', 'error');
            return;
        }
        
        state.currentFile = file;
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            elements.imagePreview.src = e.target.result;
            elements.dropZone.querySelector('.drop-zone-content').hidden = true;
            elements.previewContainer.hidden = false;
            validateForm();
            announceToScreenReader('Image uploaded successfully');
        };
        reader.readAsDataURL(file);
    }

    /**
     * Remove uploaded image
     */
    function removeImage(e) {
        e.stopPropagation();
        state.currentFile = null;
        elements.fileInput.value = '';
        elements.imagePreview.src = '';
        elements.previewContainer.hidden = true;
        elements.dropZone.querySelector('.drop-zone-content').hidden = false;
        validateForm();
        announceToScreenReader('Image removed');
    }

    /**
     * Update resolution value display
     */
    function updateResolutionValue() {
        elements.resolutionValue.textContent = `${elements.resolution.value}px`;
    }

    /**
     * Validate form and enable/disable generate button
     */
    function validateForm() {
        const hasFile = state.currentFile !== null;
        const hasDescription = elements.description.value.trim().length > 0;
        elements.generateBtn.disabled = !(hasFile && hasDescription);
    }

    /**
     * Generate design
     */
    async function generateDesign() {
        if (!state.currentFile || !elements.description.value.trim()) {
            return;
        }
        
        state.isGenerating = true;
        updateUIState('loading');
        
        try {
            // Step 1: Upload and enhance prompt
            updateLoadingStep(1);
            const formData = new FormData();
            formData.append('file', state.currentFile);
            
            // Save input file
            const inputResponse = await fetch(`${FASTAPI_URL}/save-input`, {
                method: 'POST',
                body: formData
            });
            
            if (!inputResponse.ok) {
                throw new Error('Failed to upload image');
            }
            
            const inputData = await inputResponse.json();
            
            // Enhance prompt with image
            updateLoadingStep(2);
            const enhanceResponse = await fetch(`${FASTAPI_URL}/enhance-prompt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    room_description: elements.description.value.trim(),
                    image_path: inputData.path
                })
            });
            
            if (!enhanceResponse.ok) {
                throw new Error('Failed to enhance prompt');
            }
            
            const enhanceData = await enhanceResponse.json();
            
            if (!enhanceData.success) {
                throw new Error(enhanceData.error || 'Prompt enhancement failed');
            }
            
            // Step 3: Generate image using SD prompt with task-specific ControlNet settings
            updateLoadingStep(3);
            const generateResponse = await fetch(`${FASTAPI_URL}/generate-image`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    enhanced_prompt: enhanceData.sd_prompt,  // Use SD-optimized tags
                    room_description: elements.description.value.trim(),
                    image_path: inputData.path,
                    target_resolution: parseInt(elements.resolution.value),
                    task_type: enhanceData.task_type || 'style'  // Pass task type for ControlNet adjustment
                })
            });
            
            if (!generateResponse.ok) {
                throw new Error('Failed to generate image');
            }
            
            const generateData = await generateResponse.json();
            
            if (!generateData.success) {
                throw new Error(generateData.error || 'Image generation failed');
            }
            
            // Track original image path for all iterations
            state.originalImagePath = inputData.path;
            state.originalDescription = elements.description.value.trim();
            state.iteration = 1;
            
            // Display result with both reasoning (for display) and sd_prompt (used for generation)
            state.currentResult = {
                original: inputData.url,
                staged: generateData.image_path,
                reasoning: enhanceData.reasoning,  // Display this in UI
                sd_prompt: enhanceData.sd_prompt,  // This was used for generation
                description: elements.description.value.trim(),
                iteration: state.iteration
            };
            
            displayResult(state.currentResult);
            updateIterationDisplay();
            addToHistory(state.currentResult);
            showToast('Transformation complete!', 'success');
            announceToScreenReader('Your room transformation is ready');
            
        } catch (error) {
            console.error('Generation error:', error);
            showToast(error.message || 'Failed to transform room', 'error');
            announceToScreenReader(`Error: ${error.message}`, true);
            updateUIState('empty');
        } finally {
            state.isGenerating = false;
        }
    }

    /**
     * Update loading step visual
     */
    function updateLoadingStep(step) {
        const steps = elements.loadingState.querySelectorAll('.step');
        steps.forEach((s, i) => {
            if (i < step) {
                s.classList.add('active');
            } else {
                s.classList.remove('active');
            }
        });
    }

    /**
     * Update UI state
     */
    function updateUIState(state) {
        elements.emptyState.hidden = state !== 'empty';
        elements.loadingState.hidden = state !== 'loading';
        elements.resultContent.hidden = state !== 'result';
        
        if (state === 'loading') {
            elements.generateBtn.querySelector('.btn-text').hidden = true;
            elements.generateBtn.querySelector('.btn-loading').hidden = false;
        } else {
            elements.generateBtn.querySelector('.btn-text').hidden = false;
            elements.generateBtn.querySelector('.btn-loading').hidden = true;
        }
    }

    /**
     * Display result
     */
    function displayResult(result) {
        console.log('Displaying result:', result);
        
        // Add cache-busting parameter to prevent browser caching
        const cacheBuster = `?t=${Date.now()}`;
        const imageUrl = result.staged + cacheBuster;
        
        console.log('Setting image URL:', imageUrl);
        
        // Clear previous image first to force refresh
        elements.resultStaged.removeAttribute('src');
        elements.resultStaged.removeAttribute('srcset');
        
        // Set up image load handlers
        elements.resultStaged.onload = function() {
            console.log('Image loaded successfully');
        };
        
        elements.resultStaged.onerror = function() {
            console.error('Failed to load image:', imageUrl);
            showToast('Failed to load generated image', 'error');
        };
        
        // Small delay to ensure clear happens before new src
        setTimeout(() => {
            elements.resultStaged.src = imageUrl;
        }, 10);
        
        elements.enhancedPrompt.textContent = result.reasoning;  // Display reasoning to user
        
        // Setup expand button with cache-busted URL
        if (elements.expandBtn) {
            elements.expandBtn.onclick = () => showImageModal(imageUrl);
        }
        
        updateUIState('result');
    }
    
    /**
     * Show image in modal
     */
    function showImageModal(imageSrc) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('image-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'image-modal';
            modal.className = 'image-modal';
            modal.innerHTML = `
                <button class="image-modal-close" aria-label="Close">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
                <img alt="Full size transformation">
            `;
            document.body.appendChild(modal);
            
            // Close handlers
            modal.querySelector('.image-modal-close').addEventListener('click', hideImageModal);
            modal.addEventListener('click', (e) => {
                if (e.target === modal) hideImageModal();
            });
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && modal.classList.contains('active')) {
                    hideImageModal();
                }
            });
        }
        
        modal.querySelector('img').src = imageSrc;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    /**
     * Hide image modal
     */
    function hideImageModal() {
        const modal = document.getElementById('image-modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    /**
     * Toggle collapsible section
     */
    function toggleCollapsible(e) {
        const button = e.currentTarget;
        const isExpanded = button.getAttribute('aria-expanded') === 'true';
        const content = document.getElementById(button.getAttribute('aria-controls'));
        
        button.setAttribute('aria-expanded', !isExpanded);
        content.hidden = isExpanded;
    }

    /**
     * Download result image
     */
    function downloadResult() {
        if (!state.currentResult || !state.currentResult.staged) {
            return;
        }
        
        const link = document.createElement('a');
        link.href = state.currentResult.staged;
        link.download = `transroomer-${Date.now()}.png`;
        link.click();
        showToast('Download started', 'success');
    }

    /**
     * Refine design based on user feedback
     */
    async function refineDesign() {
        const feedback = elements.feedbackInput.value.trim();
        
        if (!feedback) {
            showToast('Please enter your feedback first', 'error');
            return;
        }
        
        if (!state.currentResult) {
            showToast('No previous result to refine', 'error');
            return;
        }
        
        state.isGenerating = true;
        
        // Show loading state on refine button
        if (elements.refineBtn) {
            elements.refineBtn.querySelector('.btn-text').hidden = true;
            elements.refineBtn.querySelector('.btn-loading').hidden = false;
            elements.refineBtn.disabled = true;
        }
        
        showToast('Refining design... Please wait', 'info');
        
        try {
            const refineResponse = await fetch(`${FASTAPI_URL}/refine-design`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_feedback: feedback,
                    previous_reasoning: state.currentResult.reasoning,
                    previous_sd_prompt: state.currentResult.sd_prompt,
                    previous_result_path: state.currentResult.staged.replace('/data/outputs/', ''),  // Convert URL to path
                    original_image_path: state.originalImagePath,
                    target_resolution: parseInt(elements.resolution.value),
                    iteration: state.iteration + 1
                })
            });
            
            if (!refineResponse.ok) {
                throw new Error('Failed to refine design');
            }
            
            const refineData = await refineResponse.json();
            
            console.log('Refinement response:', refineData);
            
            if (!refineData.success) {
                console.error('Refinement failed:', refineData.error);
                throw new Error(refineData.error || 'Design refinement failed');
            }
            
            if (!refineData.image_path) {
                throw new Error('No image path returned from refinement');
            }
            
            console.log('New image path:', refineData.image_path);
            
            // Update iteration
            state.iteration++;
            
            // Update current result
            state.currentResult = {
                original: state.currentResult.original,
                staged: refineData.image_path,
                reasoning: refineData.reasoning,
                sd_prompt: refineData.sd_prompt,
                description: `${state.originalDescription} (Refined: ${feedback})`,
                iteration: state.iteration
            };
            
            // Display updated result
            displayResult(state.currentResult);
            updateIterationDisplay();
            
            // Clear feedback input
            elements.feedbackInput.value = '';
            
            showToast(`Design refined (Iteration ${state.iteration})`, 'success');
            announceToScreenReader(`Design refinement complete. Iteration ${state.iteration}.`);
            
        } catch (error) {
            console.error('Refinement error:', error);
            showToast(error.message || 'Failed to refine design', 'error');
            announceToScreenReader(`Error: ${error.message}`, true);
        } finally {
            state.isGenerating = false;
            
            // Reset refine button
            if (elements.refineBtn) {
                elements.refineBtn.querySelector('.btn-text').hidden = false;
                elements.refineBtn.querySelector('.btn-loading').hidden = true;
                elements.refineBtn.disabled = false;
            }
        }
    }
    
    /**
     * Update iteration display badge
     */
    function updateIterationDisplay() {
        if (elements.iterationBadge) {
            elements.iterationBadge.textContent = `Iteration ${state.iteration}`;
        }
    }

    /**
     * Reset form for new design
     */
    function resetForm() {
        state.currentFile = null;
        state.currentResult = null;
        state.iteration = 1;
        state.originalImagePath = null;
        state.originalDescription = null;
        elements.fileInput.value = '';
        elements.imagePreview.src = '';
        elements.previewContainer.hidden = true;
        elements.dropZone.querySelector('.drop-zone-content').hidden = false;
        elements.description.value = '';
        if (elements.feedbackInput) {
            elements.feedbackInput.value = '';
        }
        validateForm();
        updateUIState('empty');
        announceToScreenReader('Form reset. Ready for new design.');
    }

    /**
     * Add result to history
     */
    function addToHistory(result) {
        const historyItem = {
            id: Date.now(),
            ...result,
            timestamp: new Date()
        };
        
        state.history.unshift(historyItem);
        if (state.history.length > 12) {
            state.history.pop();
        }
        
        renderHistory();
    }

    /**
     * Render history grid
     */
    function renderHistory() {
        if (state.history.length === 0) {
            elements.historyGrid.innerHTML = `
                <div class="history-empty">
                    <p>No transformations yet. Create your first one above!</p>
                </div>
            `;
            return;
        }
        
        elements.historyGrid.innerHTML = state.history.map(item => `
            <div class="history-item" role="button" tabindex="0" data-id="${item.id}">
                <img src="${item.staged}" alt="Room transformation" loading="lazy">
                <div class="history-item-info">
                    <div class="history-item-date">${formatDate(item.timestamp)}</div>
                </div>
            </div>
        `).join('');
        
        // Add click handlers
        elements.historyGrid.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => loadHistoryItem(item.dataset.id));
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    loadHistoryItem(item.dataset.id);
                }
            });
        });
    }

    /**
     * Load history item
     */
    function loadHistoryItem(id) {
        const item = state.history.find(h => h.id === parseInt(id));
        if (item) {
            state.currentResult = item;
            displayResult(item);
            showToast('Transformation loaded from history', 'success');
            announceToScreenReader('Previous transformation loaded');
        }
    }

    /**
     * Format date
     */
    function formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    }

    /**
     * Show toast notification
     */
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        
        elements.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    /**
     * Theme management
     */
    function setupTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        announceToScreenReader(`${newTheme} mode enabled`);
    }

    /**
     * Load history from API (placeholder for future enhancement)
     */
    function loadHistory() {
        // Could load from localStorage or API
        const saved = localStorage.getItem('stagingHistory');
        if (saved) {
            state.history = JSON.parse(saved).map(h => ({
                ...h,
                timestamp: new Date(h.timestamp)
            }));
            renderHistory();
        }
    }

    /**
     * Save history to localStorage
     */
    function saveHistory() {
        localStorage.setItem('stagingHistory', JSON.stringify(state.history));
    }

    /**
     * Announce to screen reader
     */
    function announceToScreenReader(message, isError = false) {
        const announcement = document.createElement('div');
        announcement.setAttribute('role', isError ? 'alert' : 'status');
        announcement.setAttribute('aria-live', isError ? 'assertive' : 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.style.cssText = `
            position: absolute;
            left: -10000px;
            width: 1px;
            height: 1px;
            overflow: hidden;
        `;
        announcement.textContent = message;
        document.body.appendChild(announcement);
        
        setTimeout(() => announcement.remove(), 1000);
    }

    /**
     * Handle keyboard shortcuts
     */
    function handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + Enter to generate
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            if (!elements.generateBtn.disabled && !state.isGenerating) {
                generateDesign();
            }
        }
        
        // Escape to reset
        if (e.key === 'Escape' && state.currentResult) {
            resetForm();
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
