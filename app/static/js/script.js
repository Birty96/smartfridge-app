/*!
 * Color mode toggler for Bootstrap's docs (https://getbootstrap.com/)
 * Copyright 2011-2024 The Bootstrap Authors
 * Licensed under the Creative Commons Attribution 3.0 Unported License.
 */

(() => {
  'use strict'

  const getStoredTheme = () => localStorage.getItem('theme')
  const setStoredTheme = theme => localStorage.setItem('theme', theme)

  const getPreferredTheme = () => {
    const storedTheme = getStoredTheme()
    if (storedTheme) {
      return storedTheme
    }

    // Check system preference if no stored theme, else default to dark
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  }

  const setTheme = theme => {
    if (theme === 'auto') {
      // Use system preference if set to 'auto'
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    document.documentElement.setAttribute('data-bs-theme', theme)
  }

  // Apply theme immediately on load
  setTheme(getPreferredTheme())

  const showActiveTheme = (theme, focus = false) => {
    const themeSwitcher = document.querySelector('#bd-theme') // The dropdown button
    if (!themeSwitcher) {
      return
    }

    const themeSwitcherText = document.querySelector('#bd-theme-text') // Text inside the button
    const activeThemeIcon = document.querySelector('.theme-icon-active use') // SVG icon
    const btnToActive = document.querySelector(`[data-bs-theme-value="${theme}"]`)
    const svgOfActiveBtn = btnToActive.querySelector('svg use').getAttribute('href')

    document.querySelectorAll('[data-bs-theme-value]').forEach(element => {
      element.classList.remove('active')
      element.setAttribute('aria-pressed', 'false')
    })

    btnToActive.classList.add('active')
    btnToActive.setAttribute('aria-pressed', 'true')
    activeThemeIcon.setAttribute('href', svgOfActiveBtn)
    const themeSwitcherLabel = `${themeSwitcherText.textContent} (${btnToActive.dataset.bsThemeValue})`
    themeSwitcher.setAttribute('aria-label', themeSwitcherLabel)

    if (focus) {
      themeSwitcher.focus()
    }
  }

  // Update the active theme icon/button when the system preference changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const storedTheme = getStoredTheme()
    if (storedTheme !== 'light' && storedTheme !== 'dark') {
      // Only update if theme is 'auto' or not set
      setTheme(getPreferredTheme())
    }
  })

  // Add event listeners after the DOM is loaded
  window.addEventListener('DOMContentLoaded', () => {
    // Show the active theme in the dropdown
    showActiveTheme(getPreferredTheme())

    // Add click listeners to the theme options in the dropdown
    document.querySelectorAll('[data-bs-theme-value]')
      .forEach(toggle => {
        toggle.addEventListener('click', () => {
          const theme = toggle.getAttribute('data-bs-theme-value')
          setStoredTheme(theme) // Save the explicitly chosen theme
          setTheme(theme)      // Apply the theme
          showActiveTheme(theme, true) // Update the dropdown display
        })
      })
  })
})() 