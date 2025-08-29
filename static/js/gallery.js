class PropertyGallery {
    constructor() {
        this.currentIndex = 0;
        this.images = [];
        this.gallery = null;
        this.isOpen = false;
        this.touchStartX = 0;
        this.touchEndX = 0;
        
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
            <div id="property-gallery" class="gallery-fullscreen">
                <div class="gallery-container">
                    <div class="gallery-loading"></div>
                    <img class="gallery-image" alt="Property Image">
                    
                    <button class="gallery-nav prev" data-direction="prev">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="15,18 9,12 15,6"></polyline>
                        </svg>
                    </button>
                    
                    <button class="gallery-nav next" data-direction="next">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9,18 15,12 9,6"></polyline>
                        </svg>
                    </button>
                    
                    <button class="gallery-close">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                    
                    <div class="gallery-counter">
                        <span class="current">1</span> / <span class="total">1</span>
                    </div>
                    
                    <div class="gallery-indicators"></div>
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
        
        // Background click to close
        this.gallery.addEventListener('click', (e) => {
            if (e.target === this.gallery) {
                this.close();
            }
        });
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.isOpen) return;
            
            switch (e.key) {
                case 'Escape':
                    this.close();
                    break;
                case 'ArrowLeft':
                    this.prev();
                    break;
                case 'ArrowRight':
                    this.next();
                    break;
            }
        });
        
        // Touch events for swipe
        this.gallery.addEventListener('touchstart', (e) => {
            this.touchStartX = e.changedTouches[0].screenX;
        });
        
        this.gallery.addEventListener('touchend', (e) => {
            this.touchEndX = e.changedTouches[0].screenX;
            this.handleSwipe();
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
                const images = JSON.parse(thumbnail.dataset.galleryImages);
                this.open(images, index);
            }
        });
    }
    
    open(images, startIndex = 0) {
        this.images = images;
        this.currentIndex = startIndex;
        this.isOpen = true;
        
        // Prevent body scroll
        document.body.classList.add('gallery-open');
        
        // Show gallery
        this.gallery.classList.add('active');
        
        // Load initial image
        this.loadImage();
        
        // Update indicators
        this.updateIndicators();
        
        // Update counter
        this.updateCounter();
        
        // Update navigation buttons
        this.updateNavigation();
    }
    
    close() {
        this.isOpen = false;
        
        // Allow body scroll
        document.body.classList.remove('gallery-open');
        
        // Hide gallery
        this.gallery.classList.remove('active');
        
        // Reset image
        const img = this.gallery.querySelector('.gallery-image');
        img.classList.remove('loaded');
    }
    
    next() {
        if (this.currentIndex < this.images.length - 1) {
            this.currentIndex++;
            this.loadImage();
            this.updateIndicators();
            this.updateCounter();
            this.updateNavigation();
        }
    }
    
    prev() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.loadImage();
            this.updateIndicators();
            this.updateCounter();
            this.updateNavigation();
        }
    }
    
    goTo(index) {
        if (index >= 0 && index < this.images.length) {
            this.currentIndex = index;
            this.loadImage();
            this.updateIndicators();
            this.updateCounter();
            this.updateNavigation();
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
            const dot = document.createElement('div');
            dot.className = `gallery-dot ${index === this.currentIndex ? 'active' : ''}`;
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
        
        prevBtn.disabled = this.currentIndex === 0;
        nextBtn.disabled = this.currentIndex === this.images.length - 1;
    }
    
    handleSwipe() {
        const swipeThreshold = 50;
        const diff = this.touchStartX - this.touchEndX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                this.next(); // Swipe left - next image
            } else {
                this.prev(); // Swipe right - previous image
            }
        }
    }
}

// Initialize gallery when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PropertyGallery();
});