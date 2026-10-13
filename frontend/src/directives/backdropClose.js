const states = new WeakMap();

// A click can target the backdrop when a drag starts inside the dialog.
// Require both ends of the primary pointer gesture to be on the backdrop.
export default {
  mounted(el, binding) {
    const state = { close: binding.value, pointerId: null, releasedOnBackdrop: false };
    const reset = () => {
      state.pointerId = null;
      state.releasedOnBackdrop = false;
    };
    const onPointerDown = (event) => {
      reset();
      if (event.button === 0 && event.isPrimary && event.target === el) {
        state.pointerId = event.pointerId;
      }
    };
    const onPointerUp = (event) => {
      // Hit testing also handles touch's implicit pointer capture.
      state.releasedOnBackdrop = state.pointerId === event.pointerId
        && el.ownerDocument.elementFromPoint(event.clientX, event.clientY) === el;
    };
    const onClick = (event) => {
      const shouldClose = event.target === el && state.releasedOnBackdrop;
      reset();
      if (shouldClose) state.close(event);
    };
    const listeners = {
      pointerdown: onPointerDown,
      pointerup: onPointerUp,
      pointercancel: reset,
      click: onClick,
    };
    for (const [name, handler] of Object.entries(listeners)) {
      el.addEventListener(name, handler, true);
    }
    states.set(el, { listeners, state });
  },
  updated(el, binding) {
    states.get(el).state.close = binding.value;
  },
  unmounted(el) {
    for (const [name, handler] of Object.entries(states.get(el).listeners)) {
      el.removeEventListener(name, handler, true);
    }
    states.delete(el);
  },
};
