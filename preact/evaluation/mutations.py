"""UI mutation injection for Experiment 3 (Adaptation to UI Changes).

Implements controlled UI mutations at three severity levels:
- Minor: CSS changes, element repositioning
- Moderate: Added modals, renamed fields, reorganized navigation
- Major: Restructured layout, new sub-flows
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MutationSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


@dataclass
class UIMutation:
    """A UI mutation to inject into the test environment."""

    name: str
    severity: MutationSeverity
    description: str
    js_injection: str  # JavaScript to execute to apply the mutation
    affected_xpaths: list[str]  # XPaths that will break


# ─── Predefined Mutations ────────────────────────────────────────────────────

MINOR_MUTATIONS = [
    UIMutation(
        name="css_class_change",
        severity=MutationSeverity.MINOR,
        description="Change CSS classes on interactive elements",
        js_injection="""
            document.querySelectorAll('button, a, input').forEach(el => {
                if (el.className) {
                    el.className = el.className.replace(/btn-primary/g, 'btn-action-main');
                }
            });
        """,
        affected_xpaths=[],
    ),
    UIMutation(
        name="element_reposition",
        severity=MutationSeverity.MINOR,
        description="Reorder elements within their containers",
        js_injection="""
            document.querySelectorAll('.toolbar, .action-bar, nav').forEach(container => {
                const children = Array.from(container.children);
                if (children.length > 2) {
                    container.insertBefore(children[children.length - 1], children[0]);
                }
            });
        """,
        affected_xpaths=[],
    ),
    UIMutation(
        name="add_wrapper_div",
        severity=MutationSeverity.MINOR,
        description="Wrap elements in additional container divs",
        js_injection="""
            document.querySelectorAll('form > input, form > button').forEach(el => {
                const wrapper = document.createElement('div');
                wrapper.className = 'field-wrapper';
                el.parentNode.insertBefore(wrapper, el);
                wrapper.appendChild(el);
            });
        """,
        affected_xpaths=[],
    ),
]

MODERATE_MUTATIONS = [
    UIMutation(
        name="confirmation_modal",
        severity=MutationSeverity.MODERATE,
        description="Add a confirmation modal before submit actions",
        js_injection="""
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', function(e) {
                    e.preventDefault();
                    const modal = document.createElement('div');
                    modal.id = 'confirm-modal';
                    modal.innerHTML = `
                        <div style="position:fixed;top:0;left:0;width:100%;height:100%;
                                    background:rgba(0,0,0,0.5);z-index:9999;
                                    display:flex;align-items:center;justify-content:center">
                            <div style="background:white;padding:20px;border-radius:8px">
                                <h3>Confirm Action</h3>
                                <p>Are you sure you want to proceed?</p>
                                <button id="modal-confirm" onclick="this.closest('#confirm-modal').remove();
                                    document.querySelector('form').submit()">Confirm</button>
                                <button id="modal-cancel" onclick="this.closest('#confirm-modal').remove()">Cancel</button>
                            </div>
                        </div>`;
                    document.body.appendChild(modal);
                });
            });
        """,
        affected_xpaths=["//form//button[@type='submit']"],
    ),
    UIMutation(
        name="rename_form_fields",
        severity=MutationSeverity.MODERATE,
        description="Rename form field names and labels",
        js_injection="""
            const renames = {
                'email': 'user_email_address',
                'password': 'user_secret',
                'name': 'full_name',
                'username': 'account_id',
                'search': 'query_input'
            };
            document.querySelectorAll('input, textarea').forEach(el => {
                const name = el.name || el.id;
                if (name && renames[name]) {
                    el.name = renames[name];
                    el.id = renames[name];
                    if (el.placeholder) {
                        el.placeholder = el.placeholder.replace(name, renames[name]);
                    }
                }
            });
        """,
        affected_xpaths=[
            "//input[@name='email']",
            "//input[@name='password']",
            "//input[@name='username']",
        ],
    ),
    UIMutation(
        name="reorganize_navigation",
        severity=MutationSeverity.MODERATE,
        description="Move navigation items into a dropdown menu",
        js_injection="""
            const nav = document.querySelector('nav');
            if (nav) {
                const items = nav.querySelectorAll('a, button');
                if (items.length > 3) {
                    const dropdown = document.createElement('div');
                    dropdown.className = 'nav-dropdown';
                    dropdown.innerHTML = '<button class="dropdown-toggle">Menu ▾</button>';
                    const menu = document.createElement('div');
                    menu.className = 'dropdown-menu';
                    menu.style.display = 'none';
                    items.forEach(item => menu.appendChild(item.cloneNode(true)));
                    dropdown.appendChild(menu);
                    dropdown.querySelector('.dropdown-toggle').onclick = () => {
                        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
                    };
                    nav.innerHTML = '';
                    nav.appendChild(dropdown);
                }
            }
        """,
        affected_xpaths=["//nav//a", "//nav//button"],
    ),
]

MAJOR_MUTATIONS = [
    UIMutation(
        name="page_restructure",
        severity=MutationSeverity.MAJOR,
        description="Restructure the page layout completely",
        js_injection="""
            const main = document.querySelector('main, #content, .main-content, .container');
            if (main) {
                const sidebar = document.createElement('aside');
                sidebar.className = 'new-sidebar';
                sidebar.style.cssText = 'float:left;width:200px;padding:10px;background:#f5f5f5';

                const content = document.createElement('div');
                content.className = 'new-main-content';
                content.style.cssText = 'margin-left:220px;padding:10px';

                while (main.firstChild) {
                    content.appendChild(main.firstChild);
                }
                main.appendChild(sidebar);
                main.appendChild(content);
            }
        """,
        affected_xpaths=[],
    ),
    UIMutation(
        name="multi_step_flow",
        severity=MutationSeverity.MAJOR,
        description="Convert single-page form to multi-step wizard",
        js_injection="""
            const form = document.querySelector('form');
            if (form) {
                const inputs = form.querySelectorAll('input:not([type=hidden]), textarea, select');
                if (inputs.length > 2) {
                    const steps = [];
                    inputs.forEach((input, i) => {
                        const step = document.createElement('div');
                        step.className = 'wizard-step';
                        step.dataset.step = i;
                        step.style.display = i === 0 ? 'block' : 'none';
                        const label = input.previousElementSibling || document.createElement('label');
                        step.appendChild(label.cloneNode(true));
                        step.appendChild(input.cloneNode(true));
                        const nextBtn = document.createElement('button');
                        nextBtn.type = 'button';
                        nextBtn.textContent = i < inputs.length - 1 ? 'Next' : 'Submit';
                        nextBtn.className = 'wizard-next';
                        nextBtn.onclick = () => {
                            step.style.display = 'none';
                            const next = form.querySelector(`[data-step="${i+1}"]`);
                            if (next) next.style.display = 'block';
                        };
                        step.appendChild(nextBtn);
                        steps.push(step);
                    });
                    form.innerHTML = '';
                    steps.forEach(s => form.appendChild(s));
                }
            }
        """,
        affected_xpaths=["//form//input", "//form//button"],
    ),
]


async def apply_mutation(
    env: Any,
    mutation: UIMutation,
) -> None:
    """Apply a UI mutation to the current environment."""
    logger.info(
        "Applying mutation: %s (%s) — %s",
        mutation.name,
        mutation.severity.value,
        mutation.description,
    )
    await env.evaluate_js(mutation.js_injection)


async def apply_mutations_by_severity(
    env: Any,
    severity: MutationSeverity,
) -> list[UIMutation]:
    """Apply all mutations of a given severity level."""
    mutations_map = {
        MutationSeverity.MINOR: MINOR_MUTATIONS,
        MutationSeverity.MODERATE: MODERATE_MUTATIONS,
        MutationSeverity.MAJOR: MAJOR_MUTATIONS,
    }
    mutations = mutations_map.get(severity, [])
    for m in mutations:
        await apply_mutation(env, m)
    return mutations
