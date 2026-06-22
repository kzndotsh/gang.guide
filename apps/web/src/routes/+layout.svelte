<script lang="ts">
  import '../app.css';
  import * as Tooltip from '$lib/components/ui/tooltip/index.js';
  import { navigating } from '$app/state';
  import CustomCursor from '$lib/CustomCursor.svelte';

  let { children } = $props();
</script>

<Tooltip.Provider>
  <div class="dark h-full min-h-screen cursor-none" oncontextmenu={(e) => e.preventDefault()}>
    <CustomCursor />
    {#if navigating.to}
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-background">
        <div class="text-center">
          <div class="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-primary"></div>
          <p class="mt-3 text-sm text-muted-foreground">Loading graph…</p>
        </div>
      </div>
    {/if}
    {@render children?.()}
  </div>
</Tooltip.Provider>
