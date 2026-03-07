// 平滑滚动
function smoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// 导航栏滚动效果
function navbarScrollEffect() {
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.94)';
            navbar.style.boxShadow = '0 12px 24px rgba(16, 35, 53, 0.12)';
        } else {
            navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.84)';
            navbar.style.boxShadow = 'none';
        }
    });
}

// 功能卡片悬停效果
function featureCardEffects() {
    const cards = document.querySelectorAll('.feature-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
            this.style.boxShadow = '0 10px 20px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.05)';
        });
    });
}

// 定价卡片切换效果
function pricingCardEffects() {
    const cards = document.querySelectorAll('.pricing-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('featured')) {
                this.style.transform = 'translateY(0)';
            }
        });
    });
}

// 表单验证
function validateForms() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('input[required], textarea[required]');
            let isValid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.style.borderColor = '#dc3545';
                    input.style.boxShadow = '0 0 0 0.2rem rgba(220, 53, 69, 0.25)';
                } else {
                    input.style.borderColor = '#ced4da';
                    input.style.boxShadow = 'none';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('请填写所有必填字段');
            }
        });
        
        // 输入框焦点效果
        const inputs = form.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                this.style.borderColor = '#007bff';
                this.style.boxShadow = '0 0 0 0.2rem rgba(0, 123, 255, 0.25)';
            });
            
            input.addEventListener('blur', function() {
                if (this.value.trim()) {
                    this.style.borderColor = '#28a745';
                    this.style.boxShadow = '0 0 0 0.2rem rgba(40, 167, 69, 0.25)';
                } else {
                    this.style.borderColor = '#ced4da';
                    this.style.boxShadow = 'none';
                }
            });
        });
    });
}

// 订阅表单处理
function handleSubscribeForm() {
    const subscribeForm = document.querySelector('.subscribe-form');
    if (subscribeForm) {
        subscribeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const emailInput = this.querySelector('input[type="email"]');
            const email = emailInput.value.trim();
            
            if (email && validateEmail(email)) {
                alert('感谢您的订阅！我们会定期向您发送平台动态和营销趋势。');
                emailInput.value = '';
            } else {
                alert('请输入有效的邮箱地址');
                emailInput.style.borderColor = '#dc3545';
            }
        });
    }
}

// 邮箱验证
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// 加载首页配置
async function loadHomepageConfig() {
    try {
        const response = await fetch('/api/v1/public/config');
        if (!response.ok) return;
        const payload = await response.json();
        const homepage = payload?.homepage;
        if (!homepage) return;

        const setText = (id, value) => {
            const element = document.getElementById(id);
            if (element && value) {
                element.textContent = value;
            }
        };
        const setPlaceholder = (id, value) => {
            const element = document.getElementById(id);
            if (element && value) {
                element.placeholder = value;
            }
        };
        const isLocalStaticAsset = (value) => typeof value === 'string' && value.trim().startsWith('/static/');

        setText('site-logo', homepage.nav_brand);
        setText('nav-link-features', homepage.nav_features_label);
        setText('nav-link-scenes', homepage.nav_scenes_label);
        setText('nav-link-workflow', homepage.nav_workflow_label);
        setText('nav-link-contact', homepage.nav_contact_label);
        setText('hero-kicker', homepage.hero_kicker);
        setText('hero-title', homepage.hero_title);
        setText('hero-subtitle', homepage.hero_subtitle);
        setText('hero-photo-primary-caption', homepage.hero_photo_primary_caption);
        setText('hero-photo-secondary-caption', homepage.hero_photo_secondary_caption);
        setText('hero-photo-tertiary-caption', homepage.hero_photo_tertiary_caption);
        setText('hero-proof-primary-title', homepage.hero_proof_primary_title);
        setText('hero-proof-primary-body', homepage.hero_proof_primary_body);
        setText('hero-proof-secondary-title', homepage.hero_proof_secondary_title);
        setText('hero-proof-secondary-body', homepage.hero_proof_secondary_body);
        setText('showcase-label', homepage.showcase_label);
        setText('showcase-title', homepage.showcase_title);
        setText('showcase-subtitle', homepage.showcase_subtitle);
        setText('showcase-primary-title', homepage.showcase_primary_title);
        setText('showcase-primary-body', homepage.showcase_primary_body);
        setText('showcase-secondary-title', homepage.showcase_secondary_title);
        setText('showcase-secondary-body', homepage.showcase_secondary_body);
        setText('showcase-tertiary-title', homepage.showcase_tertiary_title);
        setText('showcase-tertiary-body', homepage.showcase_tertiary_body);
        setText('capabilities-label', homepage.capabilities_label);
        setText('capabilities-title', homepage.capabilities_title);
        setText('capabilities-subtitle', homepage.capabilities_subtitle);
        setText('capability-highlight-one', homepage.capability_highlight_one);
        setText('capability-highlight-two', homepage.capability_highlight_two);
        setText('capability-highlight-three', homepage.capability_highlight_three);
        setText('capability-spotlight-label', homepage.capability_spotlight_label);
        setText('capability-spotlight-title', homepage.capability_spotlight_title);
        setText('capability-spotlight-body', homepage.capability_spotlight_body);
        setText('capability-card-one-label', homepage.capability_card_one_label);
        setText('capability-card-one-title', homepage.capability_card_one_title);
        setText('capability-card-one-body', homepage.capability_card_one_body);
        setText('capability-card-two-label', homepage.capability_card_two_label);
        setText('capability-card-two-title', homepage.capability_card_two_title);
        setText('capability-card-two-body', homepage.capability_card_two_body);
        setText('capability-card-three-label', homepage.capability_card_three_label);
        setText('capability-card-three-title', homepage.capability_card_three_title);
        setText('capability-card-three-body', homepage.capability_card_three_body);
        setText('workflow-label', homepage.workflow_label);
        setText('workflow-title', homepage.workflow_title);
        setText('workflow-subtitle', homepage.workflow_subtitle);
        setText('workflow-step-one-title', homepage.workflow_step_one_title);
        setText('workflow-step-one-body', homepage.workflow_step_one_body);
        setText('workflow-step-two-title', homepage.workflow_step_two_title);
        setText('workflow-step-two-body', homepage.workflow_step_two_body);
        setText('workflow-step-three-title', homepage.workflow_step_three_title);
        setText('workflow-step-three-body', homepage.workflow_step_three_body);
        setText('workflow-step-four-title', homepage.workflow_step_four_title);
        setText('workflow-step-four-body', homepage.workflow_step_four_body);
        setText('workflow-summary-label', homepage.workflow_summary_label);
        setText('workflow-summary-title', homepage.workflow_summary_title);
        setText('workflow-summary-body', homepage.workflow_summary_body);
        setText('contact-section-label', homepage.contact_section_label);
        setText('contact-title', homepage.contact_section_title);
        setText('contact-subtitle', homepage.contact_section_subtitle);
        setText('contact-info-title', homepage.contact_info_title);
        setText('contact-form-label', homepage.contact_form_label);
        setText('contact-form-title', homepage.contact_form_title);
        setText('contact-form-subtitle', homepage.contact_form_subtitle);
        setText('contact-form-button', homepage.contact_form_button_text);
        setText('contact-address', homepage.contact_address);
        setText('contact-phone', homepage.contact_phone);
        setText('contact-email', homepage.contact_email);
        setText('merchant-quick-note', homepage.merchant_notice_text);
        setText('merchant-notice-title', homepage.merchant_notice_title);
        setText('merchant-notice-text', homepage.merchant_notice_text);
        setText('merchant-service-publish', homepage.merchant_service_publish_text);
        setText('merchant-service-account', homepage.merchant_service_account_text);
        setText('merchant-service-no-register', homepage.merchant_service_no_register_text);
        setText('merchant-contact-phone', homepage.merchant_contact_phone);
        setText('merchant-contact-wechat', homepage.merchant_contact_wechat);
        setText('merchant-contact-email', homepage.merchant_contact_email);
        setText('footer-about-title', homepage.footer_about_title);
        setText('footer-about-body', homepage.footer_about_body);
        setText('footer-links-title', homepage.footer_links_title);
        setText('footer-link-features', homepage.nav_features_label);
        setText('footer-link-scenes', homepage.nav_scenes_label);
        setText('footer-link-workflow', homepage.nav_workflow_label);
        setText('footer-link-contact', homepage.nav_contact_label);
        setText('footer-legal-title', homepage.footer_legal_title);
        setText('footer-privacy-label', homepage.footer_privacy_label);
        setText('footer-terms-label', homepage.footer_terms_label);
        setText('footer-cookie-label', homepage.footer_cookie_label);
        setText('footer-subscribe-title', homepage.footer_subscribe_title);
        setText('footer-subscribe-body', homepage.footer_subscribe_body);
        setPlaceholder('footer-subscribe-input', homepage.footer_subscribe_placeholder);
        setText('footer-subscribe-button', homepage.footer_subscribe_button);
        setText('footer-copyright', homepage.footer_copyright);

        const heroImage = document.getElementById('hero-image');
        if (heroImage && isLocalStaticAsset(homepage.hero_image_url)) {
            heroImage.src = homepage.hero_image_url;
            heroImage.alt = homepage.hero_title || heroImage.alt;
        }
        const heroPrimaryBtn = document.getElementById('hero-primary-btn');
        if (heroPrimaryBtn && homepage.hero_primary_button_text) {
            heroPrimaryBtn.textContent = homepage.hero_primary_button_text;
        }
        if (heroPrimaryBtn && homepage.hero_primary_button_href) {
            heroPrimaryBtn.href = homepage.hero_primary_button_href;
        }
        const heroSecondaryBtn = document.getElementById('hero-secondary-btn');
        if (heroSecondaryBtn && homepage.hero_secondary_button_text) {
            heroSecondaryBtn.textContent = homepage.hero_secondary_button_text;
        }
        if (heroSecondaryBtn && homepage.hero_secondary_button_href) {
            heroSecondaryBtn.href = homepage.hero_secondary_button_href;
        }
        if (homepage.site_name) {
            document.title = homepage.site_name;
        }
    } catch (error) {
        console.error('Load homepage config failed:', error);
    }
}

function initRevealAnimations() {
    const revealables = document.querySelectorAll('[data-reveal]');
    if (!('IntersectionObserver' in window) || !revealables.length) {
        revealables.forEach((element) => element.classList.add('is-visible'));
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
        });
    }, {
        threshold: 0.18,
        rootMargin: '0px 0px -8% 0px',
    });

    revealables.forEach((element, index) => {
        element.style.setProperty('--reveal-delay', `${Math.min(index * 70, 420)}ms`);
        observer.observe(element);
    });
}

// 初始化所有功能
function init() {
    loadHomepageConfig();
    smoothScroll();
    navbarScrollEffect();
    featureCardEffects();
    pricingCardEffects();
    validateForms();
    handleSubscribeForm();
    initRevealAnimations();
}

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', init);
