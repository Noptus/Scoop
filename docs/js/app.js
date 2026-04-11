/* ============================================
   Scoop — Frontend
   Vanilla JS, zero dependencies
   ============================================ */

(function () {
  'use strict';

  // ── Config ──────────────────────────────────
  // Signup calls Supabase directly via an RPC function (no backend needed).
  var SUPABASE_URL = 'https://oeihgepuslxpybidrquk.supabase.co';
  var SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9laWhnZXB1c2x4cHliaWRycXVrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0NzA0ODgsImV4cCI6MjA5MTA0NjQ4OH0.--NZjLdQ1nJ4GfvliLIPW9W2guttb0z1uzMa2O_O7g8';

  // ── DOM refs ────────────────────────────────
  var nav = document.getElementById('nav');
  var heroForm = document.getElementById('hero-form');
  var heroEmail = document.getElementById('hero-email');
  var signupForm = document.getElementById('signup-form');
  var btnSubmit = document.getElementById('btn-submit');
  var successEl = document.getElementById('signup-success');

  var savedEmail = '';

  // ── Nav scroll effect ───────────────────────
  window.addEventListener('scroll', function () {
    nav.classList.toggle('nav--scrolled', window.scrollY > 10);
  }, { passive: true });

  // ── Scroll reveal ───────────────────────────
  var revealElements = document.querySelectorAll('.reveal');
  var revealObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -40px 0px'
  });

  revealElements.forEach(function (el) {
    revealObserver.observe(el);
  });

  // ── Hero form: email -> scroll to setup ─────
  heroForm.addEventListener('submit', function (e) {
    e.preventDefault();
    var email = heroEmail.value.trim();

    // Remove prior error state
    heroEmail.classList.remove('hero__input--error');

    if (!email || !isValidEmail(email)) {
      heroEmail.classList.add('hero__input--error');
      heroEmail.focus();
      return;
    }

    savedEmail = email;
    scrollToSection('setup');
    setTimeout(function () { document.getElementById('product').focus(); }, 600);
  });

  // ── Signup form ─────────────────────────────
  signupForm.addEventListener('submit', function (e) {
    e.preventDefault();
    clearErrors();

    var product = document.getElementById('product');
    var customers = document.getElementById('customers');
    var productVal = product.value.trim();
    var customersRaw = customers.value.trim();

    var hasError = false;

    if (!productVal) {
      showFieldError(product, 'Tell us what you sell so we can tailor the digest.');
      hasError = true;
    } else if (productVal.length > 500) {
      showFieldError(product, 'Keep it under 500 characters.');
      hasError = true;
    }

    if (!customersRaw) {
      showFieldError(customers, 'Add at least one company to monitor.');
      hasError = true;
    }

    if (hasError) return;

    var companies = customersRaw
      .split('\n')
      .map(function (s) { return s.trim(); })
      .filter(function (s) { return s.length > 0 && s.length <= 200; })
      .slice(0, 10);

    if (!companies.length) {
      showFieldError(customers, 'Add at least one company name (max 200 chars each).');
      return;
    }

    // Start loading
    setLoading(true);

    fetch(SUPABASE_URL + '/rest/v1/rpc/signup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + SUPABASE_KEY
      },
      body: JSON.stringify({
        p_email: savedEmail,
        p_product: productVal,
        p_companies: companies
      }),
    })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (data) {
            throw new Error(data.message || 'Something went wrong.');
          });
        }
        return res.json();
      })
      .then(function (data) {
        if (data.status === 'exists') {
          showSuccess();
        } else {
          showSuccess();
        }
      })
      .catch(function (err) {
        setLoading(false);
        showFormError(err.message || 'Network error. Please try again.');
      });
  });

  // ── Input error clearing on focus ───────────
  signupForm.addEventListener('focusin', function (e) {
    var field = e.target;
    if (field.classList.contains('signup-form__input--error')) {
      field.classList.remove('signup-form__input--error');
    }
    if (field.classList.contains('signup-form__textarea--error')) {
      field.classList.remove('signup-form__textarea--error');
    }
    // Remove adjacent error message
    var next = field.nextElementSibling;
    if (next && next.classList.contains('signup-form__error')) {
      next.remove();
    }
  });

  // ── Helpers ─────────────────────────────────

  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function scrollToSection(id) {
    var target = document.getElementById(id);
    if (target) {
      window.scrollTo({
        top: target.getBoundingClientRect().top + window.scrollY - 80,
        behavior: 'smooth'
      });
    }
  }

  function showSuccess() {
    setLoading(false);
    signupForm.hidden = true;
    successEl.hidden = false;
  }

  function showFieldError(field, msg) {
    var errorClass = field.tagName === 'TEXTAREA'
      ? 'signup-form__textarea--error'
      : 'signup-form__input--error';
    field.classList.add(errorClass);

    var el = document.createElement('div');
    el.className = 'signup-form__error';
    el.setAttribute('role', 'alert');
    el.textContent = msg;
    field.after(el);

    if (!document.querySelector('.' + errorClass + ':first-of-type') || field === document.querySelector('.' + errorClass)) {
      field.focus();
    }
  }

  function showFormError(msg) {
    var existing = signupForm.querySelector('.signup-form__error--global');
    if (existing) existing.remove();

    var el = document.createElement('div');
    el.className = 'signup-form__error signup-form__error--global';
    el.setAttribute('role', 'alert');
    el.style.textAlign = 'center';
    el.style.marginTop = '12px';
    el.textContent = msg;
    btnSubmit.after(el);
  }

  function clearErrors() {
    signupForm.querySelectorAll('.signup-form__error').forEach(function (el) { el.remove(); });
    signupForm.querySelectorAll('.signup-form__input--error').forEach(function (el) { el.classList.remove('signup-form__input--error'); });
    signupForm.querySelectorAll('.signup-form__textarea--error').forEach(function (el) { el.classList.remove('signup-form__textarea--error'); });
  }

  function setLoading(loading) {
    btnSubmit.querySelector('.btn__text').hidden = loading;
    btnSubmit.querySelector('.btn__loader').hidden = !loading;
    btnSubmit.disabled = loading;
  }

  // ── Smooth scroll for anchor links ──────────
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var href = this.getAttribute('href');
      if (href === '#') return;
      var target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        scrollToSection(href.slice(1));
      }
    });
  });

})();
