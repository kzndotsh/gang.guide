<script lang="ts">
  /**
   * LaneFilter — minimal text toggles for lane groups.
   */
  interface Props {
    groups: Record<string, string[]>;
    hiddenLanes: Set<string>;
    onToggleGroup: (group: string) => void;
    onShowAll: () => void;
  }

  let { groups, hiddenLanes, onToggleGroup, onShowAll }: Props = $props();
</script>

<div class="flex flex-wrap items-center gap-x-2 gap-y-0.5 drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]">
  <button class="text-[0.7rem] text-foreground/60 hover:text-foreground" onclick={onShowAll}>All</button>
  <span class="text-muted-foreground/30">·</span>
  {#each Object.keys(groups) as group}
    {@const lanes = groups[group]}
    {@const allHidden = lanes.every((l: string) => hiddenLanes.has(l))}
    <button
      class="text-[0.7rem] transition-opacity {allHidden ? 'opacity-30 line-through' : 'opacity-100'} text-foreground/60 hover:text-foreground"
      onclick={() => onToggleGroup(group)}
    >{group}</button>
  {/each}
</div>
