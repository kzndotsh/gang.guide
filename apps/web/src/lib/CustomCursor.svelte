<script lang="ts">
  import { onMount } from 'svelte';

  let el: HTMLDivElement | undefined;
  let visible = $state(false);
  let ready = $state(false);
  let cx = 0;
  let cy = 0;
  let scale = 1;

  onMount(() => {
    const timer = setTimeout(() => { ready = true; }, 500);
    return () => clearTimeout(timer);
  });

  function applyTransform() {
    if (el) {
      el.style.transform = `translate(${cx - 10}px, ${cy - 10}px) scale(${scale})`;
    }
  }

  function onMove(e: MouseEvent) {
    cx = e.clientX;
    cy = e.clientY;
    applyTransform();
    if (!visible) visible = true;
  }

  function onDown() {
    scale = 0.75;
    applyTransform();
  }

  function onUp() {
    scale = 1;
    applyTransform();
  }
</script>

<svelte:window
  onmousemove={onMove}
  onmousedown={onDown}
  onmouseup={onUp}
  onmouseleave={() => visible = false}
  onmouseenter={() => visible = true}
/>

{#if visible && ready}
  <div
    bind:this={el}
    class="pointer-events-none fixed left-0 top-0 z-[9999] rounded-full border-2 border-foreground/70"
    style="width:20px;height:20px;will-change:transform;transition:scale 75ms ease-out;"
  >
    <div class="absolute left-1/2 top-1/2 size-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground/80"></div>
  </div>
{/if}
