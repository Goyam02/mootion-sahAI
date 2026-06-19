import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

export function GestureNavigation() {
  const navigate = useNavigate();
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);
  const isGestureCancelledRef = useRef<boolean>(false);

  useEffect(() => {
    const isScrollableX = (element: HTMLElement | null): boolean => {
      if (!element) return false;
      let el: HTMLElement | null = element;
      while (el && el !== document.body) {
        const style = window.getComputedStyle(el);
        const overflowX = style.overflowX;
        if (
          (overflowX === 'auto' || overflowX === 'scroll') &&
          el.scrollWidth > el.clientWidth
        ) {
          return true;
        }
        el = el.parentElement;
      }
      return false;
    };

    const handleTouchStart = (e: TouchEvent) => {
      // Only mobile viewports
      if (window.innerWidth >= 768) return;

      const touch = e.touches[0];
      const target = e.target as HTMLElement;

      // Ignore interactive input controls or elements with no-swipe class
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable ||
        target.closest('.no-swipe') ||
        isScrollableX(target)
      ) {
        return;
      }

      touchStartRef.current = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now(),
      };
      isGestureCancelledRef.current = false;
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!touchStartRef.current || isGestureCancelledRef.current) return;

      const touch = e.touches[0];
      const deltaX = touch.clientX - touchStartRef.current.x;
      const deltaY = touch.clientY - touchStartRef.current.y;

      const absX = Math.abs(deltaX);
      const absY = Math.abs(deltaY);

      // On first movements, check if vertical scrolling was intended
      if (absX < 10 && absY < 10) {
        return;
      }

      // If vertical movement is dominant, cancel gesture
      if (absY > absX * 1.2) {
        isGestureCancelledRef.current = true;
        return;
      }

      // Detect direction and restrict zone on start
      const startX = touchStartRef.current.x;
      const screenWidth = window.innerWidth;
      let direction: 'back' | 'forward' | null = null;

      if (startX < screenWidth * 0.35 && deltaX > 0) {
        direction = 'back';
      } else if (startX > screenWidth * 0.65 && deltaX < 0) {
        direction = 'forward';
      }

      if (!direction) {
        isGestureCancelledRef.current = true;
        return;
      }

      // Prevent default browser swipe-to-navigate gesture in Chrome/Safari if swiping near edges
      if (e.cancelable) {
        e.preventDefault();
      }
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (!touchStartRef.current || isGestureCancelledRef.current) {
        touchStartRef.current = null;
        return;
      }

      const touch = e.changedTouches[0];
      const deltaX = touch.clientX - touchStartRef.current.x;
      const startX = touchStartRef.current.x;
      const screenWidth = window.innerWidth;

      let direction: 'back' | 'forward' | null = null;

      if (startX < screenWidth * 0.35 && deltaX > 0) {
        direction = 'back';
      } else if (startX > screenWidth * 0.65 && deltaX < 0) {
        direction = 'forward';
      }

      const progress = direction && direction === 'back' ? deltaX : -deltaX;

      if (direction && progress >= 80) {
        if (direction === 'back') {
          navigate(-1);
        } else {
          navigate(1);
        }
      }

      touchStartRef.current = null;
    };

    window.addEventListener('touchstart', handleTouchStart, { passive: false });
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleTouchEnd);

    return () => {
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [navigate]);

  return null;
}
