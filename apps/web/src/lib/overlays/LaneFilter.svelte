<script lang="ts">
  /**
   * LaneFilter — pill + popover to show or hide lane groups.
   */
  import { Layers } from '@lucide/svelte';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import { Switch } from '$lib/components/ui/switch/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import { LANE_GROUP_COLORS } from '$lib/map/laneColors';

  interface Props {
    groups: Record<string, string[]>;
    hiddenLanes: Set<string>;
    onToggleGroup: (group: string) => void;
    onShowAll: () => void;
    iconOnly?: boolean;
    large?: boolean;
  }

  let { groups, hiddenLanes, onToggleGroup, onShowAll, iconOnly = false, large = false }: Props = $props();

  const groupNames = $derived(Object.keys(groups));

  function groupHidden(group: string): boolean {
    const lanes = groups[group] ?? [];
    return lanes.length > 0 && lanes.every((l) => hiddenLanes.has(l));
  }

  function groupColor(group: string): string {
    return LANE_GROUP_COLORS[group] ?? LANE_GROUP_COLORS.Regional;
  }

  const hiddenGroupCount = $derived(groupNames.filter((g) => groupHidden(g)).length);
  const visibleGroupCount = $derived(groupNames.length - hiddenGroupCount);
  const totalLaneCount = $derived(Object.values(groups).flat().length);
  const visibleLaneCount = $derived(totalLaneCount - hiddenLanes.size);
  const allVisible = $derived(hiddenGroupCount === 0);
</script>

<Popover.Root>
  <Popover.Trigger
    class="relative inline-flex shrink-0 select-none items-center justify-center rounded-full bg-muted text-[0.65rem] leading-none font-medium text-muted-foreground active:scale-[0.97] fine-hover:text-foreground {large ? 'size-9' : 'size-8 md:h-7 md:w-fit md:px-3.5'}"
    aria-label={hiddenGroupCount > 0 ? `Lanes, ${hiddenGroupCount} hidden` : 'Lanes'}
  >
    <span class="inline-flex items-center gap-1.5">
      <Layers class="size-3" strokeWidth={2} />
      {#if !iconOnly}
        Lanes
        {#if hiddenGroupCount > 0}
          <span class="tabular-nums text-muted-foreground/70">{hiddenGroupCount}</span>
        {/if}
      {:else if hiddenGroupCount > 0}
        <span class="sr-only">{hiddenGroupCount} hidden</span>
        <span
          class="absolute -top-0.5 -right-0.5 flex size-3.5 items-center justify-center rounded-full bg-primary text-[0.55rem] font-semibold tabular-nums text-primary-foreground"
          aria-hidden="true"
        >{hiddenGroupCount}</span>
      {/if}
    </span>
  </Popover.Trigger>
  <Popover.Content
    side="top"
    align="start"
    sideOffset={8}
    class="w-[min(18.5rem,calc(100vw-1.5rem))] gap-0 p-0 shadow-md"
  >
    <div class="flex items-start justify-between gap-3 px-3.5 pt-3.5 pb-3">
      <div class="min-w-0">
        <h3 class="text-sm font-semibold tracking-tight">Map lanes</h3>
        <p class="mt-1 text-[0.65rem] leading-snug text-muted-foreground">
          {visibleGroupCount} of {groupNames.length} groups · {visibleLaneCount} of {totalLaneCount} lanes visible
        </p>
      </div>
      <button
        type="button"
        class="shrink-0 rounded-md px-2 py-1 text-[0.65rem] font-medium text-primary active:scale-[0.98] fine-hover:bg-accent fine-hover:text-accent-foreground"
        onclick={onShowAll}
      >
        {allVisible ? 'Hide all' : 'Show all'}
      </button>
    </div>

    <Separator />

    <div class="flex max-h-[min(52dvh,20rem)] flex-col gap-1 overflow-y-auto overscroll-contain p-2">
      {#each groupNames as group}
        {@const hidden = groupHidden(group)}
        {@const lanes = groups[group] ?? []}
        {@const color = groupColor(group)}
        <div
          role="button"
          tabindex="0"
          class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 transition-colors fine-hover:bg-accent/50 active:scale-[0.99] {hidden ? 'bg-transparent' : 'bg-accent/20'}"
          onclick={() => onToggleGroup(group)}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onToggleGroup(group);
            }
          }}
          aria-pressed={!hidden}
        >
          <span
            class="size-2.5 shrink-0 rounded-full ring-1 ring-border/30 transition-opacity {hidden ? 'opacity-35' : 'opacity-100'}"
            style="background-color: {color}"
            aria-hidden="true"
          ></span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-[0.78rem] font-medium leading-tight {hidden ? 'text-muted-foreground' : 'text-foreground'}">{group}</span>
            <span class="text-[0.62rem] text-muted-foreground">{lanes.length} {lanes.length === 1 ? 'lane' : 'lanes'}</span>
          </span>
          <Switch
            checked={!hidden}
            size="sm"
            tabindex={-1}
            aria-hidden="true"
            class="pointer-events-none shrink-0"
          />
        </div>
      {/each}
    </div>
  </Popover.Content>
</Popover.Root>
