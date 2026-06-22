<script lang="ts">
  /**
   * MapOverlay — floating container positioned over the map canvas.
   * Use position prop: 'bottom-center' | 'bottom-right' | 'bottom-left' | 'top-right'
   */
  interface Props {
    position?: 'bottom-center' | 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
    class?: string;
    children: any;
  }

  let { position = 'bottom-right', class: className = '', children }: Props = $props();

  const positionClasses: Record<string, string> = {
    'bottom-center': 'bottom-3 left-1/2 -translate-x-1/2',
    'bottom-right': 'bottom-3 right-3',
    'bottom-left': 'bottom-3 left-3',
    'top-right': 'top-3 right-3',
    'top-left': 'top-3 left-3',
  };
</script>

<div class="absolute z-[2] px-1 py-0.5 {positionClasses[position]} {className}">
  {@render children()}
</div>
