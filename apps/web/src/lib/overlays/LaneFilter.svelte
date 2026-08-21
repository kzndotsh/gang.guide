<script lang="ts">
  /**
   * LaneFilter — pill + popover to show or hide lane groups.
   */
  import * as Popover from '$lib/components/ui/popover/index.js';

  interface Props {
    groups: Record<string, string[]>;
    hiddenLanes: Set<string>;
    onToggleGroup: (group: string) => void;
    onShowAll: () => void;
  }

  let { groups, hiddenLanes, onToggleGroup, onShowAll }: Props = $props();

  const groupNames = $derived(Object.keys(groups));

  function groupHidden(group: string): boolean {
    const lanes = groups[group] ?? [];
    return lanes.length > 0 && lanes.every((l) => hiddenLanes.has(l));
  }

  const hiddenGroupCount = $derived(groupNames.filter((g) => groupHidden(g)).length);
</script>

<Popover.Root>
  <Popover.Trigger
    class="flex h-8 shrink-0 items-center gap-1 rounded-full bg-muted px-2.5 text-[0.65rem] font-medium text-muted-foreground hover:text-foreground active:scale-[0.97] md:h-7"
    aria-label={hiddenGroupCount > 0 ? `Lanes, ${hiddenGroupCount} hidden` : 'Lanes'}
  >
    Lanes
    {#if hiddenGroupCount > 0}
      <span class="tabular-nums text-muted-foreground/70">{hiddenGroupCount}</span>
    {/if}
  </Popover.Trigger>
  <Popover.Content
    side="top"
    align="start"
    sideOffset={8}
    class="w-56 max-h-[min(60dvh,22rem)] gap-0 overflow-y-auto p-1.5 shadow-sm"
  >
    <Popover.Header class="px-2 py-1.5">
      <Popover.Title class="text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">Lanes</Popover.Title>
    </Popover.Header>
    <button
      class="flex h-8 w-full items-center rounded-md px-2 text-left text-[0.75rem] text-foreground hover:bg-accent active:scale-[0.99]"
      onclick={onShowAll}
    >
      {hiddenLanes.size === 0 ? 'Hide all' : 'Show all'}
    </button>
    <div class="flex flex-col">
      {#each groupNames as group}
        {@const hidden = groupHidden(group)}
        <button
          class="flex h-8 w-full items-center justify-between rounded-md px-2 text-left text-[0.75rem] hover:bg-accent active:scale-[0.99] {hidden ? 'text-muted-foreground/50' : 'text-foreground'}"
          onclick={() => onToggleGroup(group)}
        >
          <span class={hidden ? 'line-through' : ''}>{group}</span>
          <span class="text-[0.6rem] uppercase tracking-wide text-muted-foreground">{hidden ? 'off' : 'on'}</span>
        </button>
      {/each}
    </div>
  </Popover.Content>
</Popover.Root>
