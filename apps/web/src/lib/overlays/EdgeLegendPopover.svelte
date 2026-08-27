<script lang="ts">
  import { GitBranch } from '@lucide/svelte';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import EdgeLegend from '$lib/overlays/EdgeLegend.svelte';

  interface Props {
    iconOnly?: boolean;
    large?: boolean;
  }

  let { iconOnly = false, large = false }: Props = $props();
</script>

<Popover.Root>
  <Popover.Trigger
    class="relative inline-flex shrink-0 select-none items-center justify-center rounded-full bg-muted text-[0.65rem] leading-none font-medium text-muted-foreground active:scale-[0.97] fine-hover:text-foreground {large ? 'size-9' : 'size-8 md:h-7 md:w-fit md:px-3.5'}"
    aria-label="Edge color legend"
  >
    <span class="inline-flex items-center gap-1.5">
      <GitBranch class="size-3" strokeWidth={2} />
      {#if !iconOnly}
        Legend
      {/if}
    </span>
  </Popover.Trigger>
  <Popover.Content side="top" align="end" sideOffset={8} class="w-auto p-2.5 shadow-sm">
    <EdgeLegend />
  </Popover.Content>
</Popover.Root>
