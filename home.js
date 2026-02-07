// static/js/home.js
document.addEventListener('DOMContentLoaded', function() {
    // Анимация появления элементов при скролле
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);

    // Наблюдаем за всеми элементами с анимацией
    document.querySelectorAll('.fade-in').forEach(el => {
        observer.observe(el);
    });

    // Плавная прокрутка для якорных ссылок
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            if (href === '#') return;
            
            e.preventDefault();
            const targetElement = document.querySelector(href);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Анимация для плавающих карточек
    const floatingCards = document.querySelectorAll('.floating-card');
    floatingCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.5}s`;
    });

    // Динамическое изменение шапки при скролле
    const header = document.querySelector('.header');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            header.style.boxShadow = '0 5px 20px rgba(0,0,0,0.1)';
            header.style.background = 'rgba(255,255,255,0.95)';
            header.style.backdropFilter = 'blur(10px)';
        } else {
            header.style.boxShadow = 'var(--shadow-light)';
            header.style.background = 'white';
            header.style.backdropFilter = 'none';
        }
        
        lastScroll = currentScroll;
    });

    // Анимация для статистики
    const statNumbers = document.querySelectorAll('.stat-number');
    const statSection = document.querySelector('.hero-stats');
    
    const statObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                statNumbers.forEach(stat => {
                    const finalValue = stat.textContent;
                    stat.textContent = '0';
                    
                    let counter = 0;
                    const increment = parseInt(finalValue) / 50;
                    
                    const timer = setInterval(() => {
                        counter += increment;
                        stat.textContent = Math.floor(counter);
                        
                        if (counter >= parseInt(finalValue)) {
                            stat.textContent = finalValue;
                            clearInterval(timer);
                        }
                    }, 30);
                });
                
                statObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    if (statSection) {
        statObserver.observe(statSection);
    }
});