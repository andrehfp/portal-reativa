class PropertyGallery {
    constructor() {
        this.currentIndex = 0;
        this.images = [];
        this.gallery = null;
        this.isOpen = false;
        this.touchStartX = 0;
        this.touchEndX = 0;
        this.touchStartY = 0;
        this.touchEndY = 0;
        this.isZoomed = false;
        this.scale = 1;
        this.preloadedImages = new Map();
        this.animationFrame = null;
        this.isDragging = false;
        this.lastTapTime = 0;
        this.panX = 0;
        this.panY = 0;
        
        this.init();
    }
    
    init() {
        // Create gallery HTML structure
        this.createGalleryHTML();
        
        // Bind events
        this.bindEvents();
    }
    
    createGalleryHTML() {
        const galleryHTML = `
            <div id="property-gallery" class="gallery-fullscreen" role="dialog" aria-label="Property image gallery" aria-modal="true">
                <div class="gallery-container">
                    <div class="gallery-loading" aria-label="Loading image"></div>
                    <div class="gallery-image-container">
                        <img class="gallery-image" alt="Property Image" draggable="false">
                    </div>
                    
                    <button class="gallery-nav prev" data-direction="prev" aria-label="Previous image">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="15,18 9,12 15,6"></polyline>
                        </svg>
                    </button>
                    
                    <button class="gallery-nav next" data-direction="next" aria-label="Next image">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9,18 15,12 9,6"></polyline>
                        </svg>
                    </button>
                    
                    <div class="gallery-top-controls">
                        <div class="gallery-counter">
                            <span class="current">1</span> / <span class="total">1</span>
                        </div>
                        
                        <div class="gallery-actions">
                            <button class="gallery-zoom-toggle" aria-label="Toggle zoom">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="11" cy="11" r="8"></circle>
                                    <path d="m21 21-4.35-4.35"></path>
                                    <line x1="11" y1="8" x2="11" y2="14"></line>
                                    <line x1="8" y1="11" x2="14" y2="11"></line>
                                </svg>
                            </button>
                            
                            <button class="gallery-fullscreen-toggle" aria-label="Toggle fullscreen">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="m21 21-6-6m6 6v-4.8m0 4.8h-4.8"></path>
                                    <path d="M3 16.2V21m0 0h4.8M3 21l6-6"></path>
                                    <path d="M21 7.8V3m0 0h-4.8M21 3l-6 6"></path>
                                    <path d="M3 7.8V3m0 0h4.8M3 3l6 6"></path>
                                </svg>
                            </button>
                            
                            <button class="gallery-close" aria-label="Close gallery">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="18" y1="6" x2="6" y2="18"></line>
                                    <line x1="6" y1="6" x2="18" y2="18"></line>
                                </svg>
                            </button>
                        </div>
                    </div>
                    
                    <div class="gallery-indicators" role="tablist" aria-label="Image indicators"></div>
                    
                    <div class="gallery-thumbnails">
                        <div class="gallery-thumbnails-track"></div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', galleryHTML);
        this.gallery = document.getElementById('property-gallery');
    }
    
    bindEvents() {
        // Gallery navigation
        this.gallery.querySelector('.gallery-nav.prev').addEventListener('click', () => this.prev());
        this.gallery.querySelector('.gallery-nav.next').addEventListener('click', () => this.next());
        this.gallery.querySelector('.gallery-close').addEventListener('click', () => this.close());
        
        // New action buttons
        this.gallery.querySelector('.gallery-zoom-toggle').addEventListener('click', () => this.toggleZoom());
        this.gallery.querySelector('.gallery-fullscreen-toggle').addEventListener('click', () => this.toggleFullscreen());
        
        // Background click to close (only if not zoomed)
        this.gallery.addEventListener('click', (e) => {
            if (e.target === this.gallery && !this.isZoomed) {
                this.close();
            }
        });
        
        // Enhanced keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.isOpen) return;
            
            switch (e.key) {
                case 'Escape':
                    if (this.isZoomed) {
                        this.resetZoom();
                    } else {
                        this.close();
                    }
                    break;
                case 'ArrowLeft':
                    this.prev();
                    break;
                case 'ArrowRight':
                    this.next();
                    break;
                case 'ArrowUp':
                    this.prev();
                    break;
                case 'ArrowDown':
                    this.next();
                    break;
                case ' ':
                    e.preventDefault();
                    this.next();
                    break;
                case 'Home':
                    this.goTo(0);
                    break;
                case 'End':
                    this.goTo(this.images.length - 1);
                    break;
                case '+':
                case '=':
                    this.zoomIn();
                    break;
                case '-':
                    this.zoomOut();
                    break;
                case '0':
                    this.resetZoom();
                    break;
                case 'f':
                case 'F11':
                    e.preventDefault();
                    this.toggleFullscreen();
                    break;
                default:
                    // Number keys for direct navigation
                    if (e.key >= '1' && e.key <= '9') {
                        const index = parseInt(e.key) - 1;
                        if (index < this.images.length) {
                            this.goTo(index);
                        }
                    }
            }
        });
        
        // Enhanced touch events
        this.bindTouchEvents();
        
        // Mouse wheel for zoom and navigation
        this.gallery.addEventListener('wheel', (e) => {
            if (!this.isOpen) return;
            e.preventDefault();
            
            if (e.ctrlKey || e.metaKey) {
                // Zoom with Ctrl/Cmd + wheel
                if (e.deltaY < 0) {
                    this.zoomIn();
                } else {
                    this.zoomOut();
                }
            } else {
                // Navigate with wheel
                if (e.deltaY > 0) {
                    this.next();
                } else {
                    this.prev();
                }
            }
        }, { passive: false });
        
        // Double click to zoom
        this.gallery.querySelector('.gallery-image').addEventListener('dblclick', () => {
            this.toggleZoom();
        });
        
        // Bind thumbnail clicks
        this.bindThumbnailClicks();
    }
    
    bindThumbnailClicks() {
        document.addEventListener('click', (e) => {
            // Check if clicked element is a gallery thumbnail
            const thumbnail = e.target.closest('[data-gallery-index]');
            if (thumbnail) {
                e.preventDefault();
                const index = parseInt(thumbnail.dataset.galleryIndex);
                
                try {
                    // Try to parse the JSON data
                    let imagesData = thumbnail.dataset.galleryImages;
                    
                    if (typeof imagesData === 'string' && imagesData.trim()) {
                        // Parse as JSON directly (now properly escaped in template)
                        const images = JSON.parse(imagesData);
                        this.open(images, index);
                    } else {
                        throw new Error('No gallery data found');
                    }
                } catch (error) {
                    console.error('Error parsing gallery images data:', error);
                    console.log('Raw data:', thumbnail.dataset.galleryImages);
                    
                    // Fallback: try to get images from all gallery elements
                    const allGalleryElements = document.querySelectorAll('[data-gallery-index]');
                    const fallbackImages = [];
                    
                    allGalleryElements.forEach(element => {
                        const img = element.querySelector('img');
                        if (img && img.src) {
                            fallbackImages.push(img.src);
                        }
                    });
                    
                    if (fallbackImages.length > 0) {
                        this.open(fallbackImages, index);
                    } else {
                        console.error('Unable to load gallery images. Please refresh the page and try again.');
                    }
                }
            }
        });
    }
    
    open(images, startIndex = 0) {
        this.images = images;
        this.currentIndex = startIndex;
        this.isOpen = true;
        
        // Reset zoom state
        this.resetZoom();
        
        // Prevent body scroll
        document.body.classList.add('gallery-open');
        
        // Show gallery
        this.gallery.classList.add('active');
        
        // Load initial image
        this.loadImage();
        
        // Preload adjacent images
        this.preloadAdjacentImages();
        
        // Update indicators
        this.updateIndicators();
        
        // Update thumbnails
        this.updateThumbnails();
        
        // Update counter
        this.updateCounter();
        
        // Update navigation buttons
        this.updateNavigation();
        
        // Focus management for accessibility
        this.gallery.focus();
        
        // Announce to screen readers
        this.announceToScreenReader(`Gallery opened. Viewing image ${this.currentIndex + 1} of ${this.images.length}`);
    }
    
    close() {
        this.isOpen = false;
        
        // Reset zoom state
        this.resetZoom();
        
        // Allow body scroll
        document.body.classList.remove('gallery-open');
        
        // Hide gallery
        this.gallery.classList.remove('active');
        
        // Reset image
        const img = this.gallery.querySelector('.gallery-image');
        img.classList.remove('loaded');
        
        // Clear preloaded images to save memory
        this.preloadedImages.clear();
        
        // Announce to screen readers
        this.announceToScreenReader('Gallery closed');
        
        // Return focus to trigger element
        const trigger = document.querySelector(`[data-gallery-index="${this.currentIndex}"]`);
        if (trigger) trigger.focus();
    }
    
    next() {
        // Wrap around to the beginning if at the end
        this.currentIndex = this.currentIndex < this.images.length - 1 ? this.currentIndex + 1 : 0;
        this.resetZoom();
        this.loadImage();
        this.preloadAdjacentImages();
        this.updateIndicators();
        this.updateThumbnails();
        this.updateCounter();
        this.updateNavigation();
        this.announceToScreenReader(`Image ${this.currentIndex + 1} of ${this.images.length}`);
    }
    
    prev() {
        // Wrap around to the end if at the beginning
        this.currentIndex = this.currentIndex > 0 ? this.currentIndex - 1 : this.images.length - 1;
        this.resetZoom();
        this.loadImage();
        this.preloadAdjacentImages();
        this.updateIndicators();
        this.updateThumbnails();
        this.updateCounter();
        this.updateNavigation();
        this.announceToScreenReader(`Image ${this.currentIndex + 1} of ${this.images.length}`);
    }
    
    goTo(index) {
        if (index >= 0 && index < this.images.length && index !== this.currentIndex) {
            this.currentIndex = index;
            this.resetZoom();
            this.loadImage();
            this.preloadAdjacentImages();
            this.updateIndicators();
            this.updateThumbnails();
            this.updateCounter();
            this.updateNavigation();
            this.announceToScreenReader(`Image ${this.currentIndex + 1} of ${this.images.length}`);
        }
    }
    
    loadImage() {
        const img = this.gallery.querySelector('.gallery-image');
        const loading = this.gallery.querySelector('.gallery-loading');
        
        // Show loading
        loading.style.display = 'block';
        img.classList.remove('loaded');
        
        // Load new image
        const newImg = new Image();
        newImg.onload = () => {
            img.src = newImg.src;
            img.alt = `Property Image ${this.currentIndex + 1}`;
            img.classList.add('loaded');
            loading.style.display = 'none';
        };
        
        newImg.onerror = () => {
            loading.style.display = 'none';
            img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300"><rect width="400" height="300" fill="%23f3f4f6"/><text x="200" y="150" text-anchor="middle" dy=".3em" fill="%239ca3af" font-family="Arial, sans-serif" font-size="16">Erro ao carregar imagem</text></svg>';
            img.classList.add('loaded');
        };
        
        newImg.src = this.images[this.currentIndex];
    }
    
    updateIndicators() {
        const indicators = this.gallery.querySelector('.gallery-indicators');
        
        if (this.images.length <= 1) {
            indicators.style.display = 'none';
            return;
        }
        
        indicators.style.display = 'flex';
        indicators.innerHTML = '';
        
        this.images.forEach((_, index) => {
            const dot = document.createElement('button');
            dot.className = `gallery-dot ${index === this.currentIndex ? 'active' : ''}`;
            dot.setAttribute('role', 'tab');
            dot.setAttribute('aria-selected', index === this.currentIndex);
            dot.setAttribute('aria-label', `Go to image ${index + 1}`);
            dot.addEventListener('click', () => this.goTo(index));
            indicators.appendChild(dot);
        });
    }
    
    updateCounter() {
        const current = this.gallery.querySelector('.gallery-counter .current');
        const total = this.gallery.querySelector('.gallery-counter .total');
        
        current.textContent = this.currentIndex + 1;
        total.textContent = this.images.length;
    }
    
    updateNavigation() {
        const prevBtn = this.gallery.querySelector('.gallery-nav.prev');
        const nextBtn = this.gallery.querySelector('.gallery-nav.next');
        
        // With wrap-around, buttons are never disabled
        prevBtn.disabled = false;
        nextBtn.disabled = false;
    }
    
    handleSwipe() {
        const swipeThreshold = 50;
        const diffX = this.touchStartX - this.touchEndX;
        const diffY = this.touchStartY - this.touchEndY;
        
        // Only handle horizontal swipes if not zoomed
        if (!this.isZoomed && Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > swipeThreshold) {
            if (diffX > 0) {
                this.next(); // Swipe left - next image
            } else {
                this.prev(); // Swipe right - previous image
            }
        }
    }
    
    // Enhanced touch events
    bindTouchEvents() {
        let initialDistance = 0;
        let lastTouchTime = 0;
        
        this.gallery.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
            
            if (e.touches.length === 2) {
                // Pinch to zoom start
                initialDistance = this.getTouchDistance(e.touches[0], e.touches[1]);
            }
            
            // Double tap detection
            const now = Date.now();
            if (now - lastTouchTime < 300) {
                this.toggleZoom();
            }
            lastTouchTime = now;
        });
        
        this.gallery.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2 && initialDistance > 0) {
                // Pinch to zoom
                e.preventDefault();
                const currentDistance = this.getTouchDistance(e.touches[0], e.touches[1]);
                const scale = currentDistance / initialDistance;
                this.setZoom(this.scale * scale);
            }
        }, { passive: false });
        
        this.gallery.addEventListener('touchend', (e) => {
            if (e.changedTouches.length === 1) {
                this.touchEndX = e.changedTouches[0].clientX;
                this.touchEndY = e.changedTouches[0].clientY;
                this.handleSwipe();
            }
            initialDistance = 0;
        });
    }
    
    getTouchDistance(touch1, touch2) {
        return Math.sqrt(
            Math.pow(touch2.clientX - touch1.clientX, 2) + 
            Math.pow(touch2.clientY - touch1.clientY, 2)
        );
    }
    
    // Zoom functionality
    toggleZoom() {
        if (this.isZoomed) {
            this.resetZoom();
        } else {
            this.setZoom(2);
        }
    }
    
    zoomIn() {
        this.setZoom(Math.min(this.scale * 1.5, 4));
    }
    
    zoomOut() {
        this.setZoom(Math.max(this.scale / 1.5, 1));
    }
    
    setZoom(newScale) {
        this.scale = Math.max(1, Math.min(newScale, 4));
        const img = this.gallery.querySelector('.gallery-image');
        
        if (this.scale > 1) {
            this.isZoomed = true;
            img.style.transform = `scale(${this.scale})`;
            img.style.cursor = 'grab';
            this.gallery.classList.add('zoomed');
        } else {
            this.resetZoom();
        }
    }
    
    resetZoom() {
        this.scale = 1;
        this.isZoomed = false;
        this.panX = 0;
        this.panY = 0;
        const img = this.gallery.querySelector('.gallery-image');
        img.style.transform = '';
        img.style.cursor = '';
        this.gallery.classList.remove('zoomed');
    }
    
    // Fullscreen functionality
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.gallery.requestFullscreen().catch(err => {
                console.log(`Error attempting to enable fullscreen: ${err.message}`);
            });
        } else {
            document.exitFullscreen();
        }
    }
    
    // Image preloading
    preloadAdjacentImages() {
        const preloadIndexes = [
            this.currentIndex - 1,
            this.currentIndex + 1
        ].filter(index => index >= 0 && index < this.images.length);
        
        preloadIndexes.forEach(index => {
            if (!this.preloadedImages.has(index)) {
                const img = new Image();
                img.src = this.images[index];
                this.preloadedImages.set(index, img);
            }
        });
    }
    
    // Update thumbnails
    updateThumbnails() {
        const track = this.gallery.querySelector('.gallery-thumbnails-track');
        
        if (this.images.length <= 1) {
            this.gallery.querySelector('.gallery-thumbnails').style.display = 'none';
            return;
        }
        
        if (!track.children.length) {
            // Create thumbnails
            this.images.forEach((src, index) => {
                const thumb = document.createElement('div');
                thumb.className = 'gallery-thumbnail';
                thumb.innerHTML = `<img src="${src}" alt="Thumbnail ${index + 1}">`;
                thumb.addEventListener('click', () => this.goTo(index));
                track.appendChild(thumb);
            });
        }
        
        // Update active thumbnail
        track.querySelectorAll('.gallery-thumbnail').forEach((thumb, index) => {
            thumb.classList.toggle('active', index === this.currentIndex);
        });
        
        // Scroll to center the active thumbnail
        this.centerActiveThumbnail();
        
        this.gallery.querySelector('.gallery-thumbnails').style.display = 'block';
    }
    
    // Center the active thumbnail in the scrollable track
    centerActiveThumbnail() {
        const container = this.gallery.querySelector('.gallery-thumbnails');
        const track = this.gallery.querySelector('.gallery-thumbnails-track');
        const thumbnails = track.querySelectorAll('.gallery-thumbnail');
        const activeThumbnail = thumbnails[this.currentIndex];
        
        if (!activeThumbnail || thumbnails.length <= 1 || !container) return;
        
        // Wait for next frame to ensure dimensions are available
        requestAnimationFrame(() => {
            const containerWidth = container.clientWidth;
            const trackWidth = track.scrollWidth;
            
            // If all thumbnails fit in container, no need to scroll
            if (trackWidth <= containerWidth) return;
            
            const thumbnailWidth = activeThumbnail.offsetWidth;
            const gap = 8; // Gap between thumbnails
            const padding = 8; // Track padding
            
            // Calculate the left position of the active thumbnail relative to the track
            const thumbnailLeft = padding + (this.currentIndex * (thumbnailWidth + gap));
            
            // Calculate scroll position to center the active thumbnail
            const targetScrollLeft = thumbnailLeft - (containerWidth / 2) + (thumbnailWidth / 2);
            
            // Clamp the scroll position to valid range
            const maxScroll = trackWidth - containerWidth;
            const scrollLeft = Math.max(0, Math.min(targetScrollLeft, maxScroll));
            
            // Smooth scroll to the calculated position
            container.scrollTo({
                left: scrollLeft,
                behavior: 'smooth'
            });
        });
    }
    
    // Accessibility helper
    announceToScreenReader(message) {
        // Create or update screen reader announcement
        let announcement = document.getElementById('gallery-sr-announcement');
        if (!announcement) {
            announcement = document.createElement('div');
            announcement.id = 'gallery-sr-announcement';
            announcement.setAttribute('aria-live', 'polite');
            announcement.setAttribute('aria-atomic', 'true');
            announcement.style.position = 'absolute';
            announcement.style.left = '-10000px';
            announcement.style.width = '1px';
            announcement.style.height = '1px';
            announcement.style.overflow = 'hidden';
            document.body.appendChild(announcement);
        }
        
        announcement.textContent = message;
    }
}

// Initialize gallery when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PropertyGallery();
});