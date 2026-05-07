
        // FAQ Data
        const faqs = [
            {
                q: "How do I download my books for offline reading?",
                a: "Go to your Library → click the three dots on any book → select 'Download'. The book will be saved in your device storage and works perfectly without internet."
            },
            {
                q: "I forgot my password. How do I reset it?",
                a: "On the login page, click 'Forgot Password'. We'll send a secure reset link to your registered email. The link expires in 15 minutes."
            },
            {
                q: "Why is my payment not going through?",
                a: "Please check your card details, ensure sufficient balance, and try again. If the issue persists, try a different payment method or contact your bank."
            },
            {
                q: "Can I cancel my subscription anytime?",
                a: "Yes! Go to Account Settings → Subscription → Cancel. You will continue to have access until the end of your current billing period."
            },
            {
                q: "The app is crashing on my phone. What should I do?",
                a: "Try force closing the app, clearing cache, or reinstalling. If it still crashes, please tell us your phone model and Android/iOS version."
            },
            {
                q: "How do I request a refund?",
                a: "Refunds are available within 14 days of purchase if you haven't downloaded the book. Go to My Purchases → Request Refund and our team will review it instantly."
            },
            {
                q: "Can I share my account with family?",
                a: "Each account is for individual use. However, you can upgrade to our Family Plan (coming soon) which allows up to 4 members."
            }
        ];

        // Render FAQs
        function renderFAQs(filteredFAQs) {
            const container = document.getElementById('faq-list');
            container.innerHTML = '';
            
            if (filteredFAQs.length === 0) {
                container.innerHTML = `<p style="text-align:center; padding:40px; font-size:18px; color:#9ca3af;">No matching questions found.<br>Try different keywords or <a href="#" onclick="showContactForm()" style="color:#4b5f61">contact support</a>.</p>`;
                return;
            }
            
            filteredFAQs.forEach((faq, index) => {
                const div = document.createElement('div');
                div.className = 'faq-item';
                div.innerHTML = `
                    <div class="faq-question" onclick="toggleFAQ(this)">
                        <span>${faq.q}</span>
                        <span class="faq-toggle">▼</span>
                    </div>
                    <div class="faq-answer">
                        ${faq.a}
                    </div>
                `;
                container.appendChild(div);
            });
        }

        // Toggle FAQ accordion
        function toggleFAQ(element) {
            const item = element.parentElement;
            item.classList.toggle('active');
        }

        // Search FAQs
        function searchFAQs() {
            const term = document.getElementById('faq-search').value.toLowerCase().trim();
            
            if (!term) {
                renderFAQs(faqs);
                return;
            }
            
            const filtered = faqs.filter(faq => 
                faq.q.toLowerCase().includes(term) || 
                faq.a.toLowerCase().includes(term)
            );
            
            renderFAQs(filtered);
            
            // Scroll to FAQ section
            document.getElementById('faq').scrollIntoView({ behavior: 'smooth' });
        }

        // Show contact form (already visible, but for quick links)
        function showContactForm() {
            document.getElementById('contact-form').scrollIntoView({ behavior: 'smooth' });
        }

        // Submit ticket simulation
        function submitTicket() {
            const name = document.getElementById('name').value;
            const ticketId = `DS-${Math.floor(100000 + Math.random() * 900000)}`;
            const displayName = (name || '').trim() || 'there';
            const message = `Thank you, ${displayName}!\nYour support ticket has been submitted.\nOur team will reply within 2 hours. Ticket #${ticketId}`;

            if (typeof window.showAppToast === 'function') {
                window.showAppToast(message, { tone: 'success', duration: 4200 });
            }
            
            // Reset form
            document.getElementById('message').value = '';
            document.getElementById('order-id').value = '';
        }

        // Live chat simulation
        function startLiveChat() {
            const message = 'Live chat opened. A support agent will be with you in a few seconds.';
            if (typeof window.showAppToast === 'function') {
                window.showAppToast(message, { tone: 'info', duration: 3200 });
            }
        }

        // Scroll helper for quick cards
        function scrollToSection(id) {
            if (id === 'faq') {
                document.getElementById('faq').scrollIntoView({ behavior: 'smooth' });
            }
        }

        // Initialize everything
        window.onload = function() {
            renderFAQs(faqs);
            
            // Allow Enter key in hero search
            document.getElementById('faq-search').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchFAQs();
                }
            });
            
            console.log('%c✅ Beautiful DigiShelf Support Page created!\n• Same exact design & colors\n• Interactive FAQ accordion\n• Live search in FAQs\n• Hover animations\n• Ready to use', 'color: #4b5f61; font-size: 15px; font-weight: bold');
        };