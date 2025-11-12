function trackEvent(eventName,parameters={}){if(typeof gtag!=='undefined'){gtag('event',eventName,parameters);}}
document.addEventListener("DOMContentLoaded",async()=>{const pricingContainer=document.getElementById("pricing-container");pricingContainer.innerHTML=`
        <p style="text-align:center; color:#00ffd0;">
            در حال بارگذاری تعرفه‌ها...
        </p>
    `;try{const response=await fetch("/get_pricing/");if(!response.ok)throw new Error("خطا در دریافت تعرفه‌ها");const plans=await response.json();if(!plans||plans.length===0){pricingContainer.innerHTML=`
                <p style="text-align:center; color:#ff3c3c;">
                    هیچ پلنی یافت نشد 😕
                </p>`;return;}
pricingContainer.innerHTML=plans.map((plan,index)=>{const isPopular=plan.popular;return`
            <div class="pricing-card ${isPopular ? 'popular' : ''} lazy-load">
                <div class="pricing-header">
                    <h3 class="pricing-name">${plan.name}</h3>
                    <div class="price">${plan.monthly_price_toman.toLocaleString()} <span>تومان/ماه</span></div>
                </div>
                <ul class="pricing-features">
                    <li><i class="fas fa-check"></i> ${plan.cpu} هسته پردازنده</li>
                    <li><i class="fas fa-check"></i> ${plan.ram_gb} گیگابایت رم</li>
                    <li><i class="fas fa-check"></i> ${plan.ssd_gb} گیگابایت فضای SSD</li>
                    <li><i class="fas fa-check"></i> ترافیک ${plan.traffic_gb === 'نامحدود' ? 'نامحدود' : plan.traffic_gb + ' گیگابایت'}</li>
                    <li><i class="fas fa-check"></i> پشتیبانی ۲۴/۷</li>
                </ul>
                <a href="#order" class="btn btn-primary" onclick="trackEvent('click', { event_category: 'engagement', event_label: 'pricing_plan_purchase', value: '${plan.name}' })">خرید پلن</a>
            </div>
        `}).join("");const lazyObserver=new IntersectionObserver((entries)=>{entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('visible');lazyObserver.unobserve(entry.target);}});},{rootMargin:'0px 0px 100px 0px'});document.querySelectorAll(".pricing-card").forEach(card=>{lazyObserver.observe(card);});}catch(error){console.error("❌ خطا در دریافت تعرفه‌ها:",error);pricingContainer.innerHTML=`
            <p style="text-align:center; color:#ff3c3c;">
                خطا در بارگذاری تعرفه‌ها 😔
            </p>`;}
const allLazyElements=document.querySelectorAll('.lazy-load');const globalLazyObserver=new IntersectionObserver((entries)=>{entries.forEach(entry=>{if(entry.isIntersecting){if(entry.target.tagName==='IMG'&&entry.target.hasAttribute('data-src')){entry.target.src=entry.target.getAttribute('data-src');entry.target.removeAttribute('data-src');}
entry.target.classList.add('visible');globalLazyObserver.unobserve(entry.target);}});},{rootMargin:'0px 0px 100px 0px'});allLazyElements.forEach(element=>{globalLazyObserver.observe(element);});const header=document.getElementById('header');if(header){window.addEventListener('scroll',function(){if(window.scrollY>100){header.classList.add('scrolled');}else{header.classList.remove('scrolled');}});}
const mobileMenuBtn=document.querySelector('.mobile-menu-btn');const nav=document.querySelector('nav ul');if(mobileMenuBtn&&nav){mobileMenuBtn.addEventListener('click',function(){nav.classList.toggle('active');const isExpanded=nav.classList.contains('active');mobileMenuBtn.setAttribute('aria-expanded',isExpanded);});}
const backToTopBtn=document.getElementById('back-to-top');if(backToTopBtn){window.addEventListener('scroll',function(){if(window.scrollY>300){backToTopBtn.classList.add('show');}else{backToTopBtn.classList.remove('show');}});backToTopBtn.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});}
document.querySelectorAll('a[href^="#"]').forEach(anchor=>{anchor.addEventListener('click',function(e){const targetId=this.getAttribute('href');const targetElement=document.querySelector(targetId);if(targetElement){e.preventDefault();const headerOffset=80;const elementPosition=targetElement.offsetTop;const offsetPosition=elementPosition-headerOffset;window.scrollTo({top:offsetPosition,behavior:'smooth'});trackEvent('click',{event_category:'navigation',event_label:'anchor_link',value:targetId});if(nav&&nav.classList.contains('active')){nav.classList.remove('active');mobileMenuBtn.setAttribute('aria-expanded','false');}}});});document.querySelectorAll('form').forEach(form=>{form.addEventListener('submit',function(e){trackEvent('submit',{event_category:'engagement',event_label:'form_submission',value:this.id||'unknown_form'});});});document.querySelectorAll('.social-icons a').forEach(link=>{link.addEventListener('click',function(e){const href=this.getAttribute('href');const platform=href.includes('telegram')?'telegram':href.includes('instagram')?'instagram':href.includes('twitter')?'twitter':href.includes('linkedin')?'linkedin':'unknown';trackEvent('click',{event_category:'social',event_label:'social_link_'+platform});});});});;