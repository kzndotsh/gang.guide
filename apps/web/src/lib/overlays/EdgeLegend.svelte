<script lang="ts">
  const items: Array<{color: string; label: string; dasharray: string; linecap: 'butt' | 'round'; arrow?: boolean}> = [
    { color: '#ff4444', label: 'Rivalry', dasharray: '4,2', linecap: 'butt' },
    { color: '#3fff8a', label: 'Alliance', dasharray: '0.5,4', linecap: 'round' },
    { color: '#b87fff', label: 'Nation', dasharray: 'none', linecap: 'butt', arrow: true },
    { color: '#ffb938', label: 'Spin-off', dasharray: 'none', linecap: 'butt', arrow: true },
  ];
</script>

<div class="flex flex-col gap-0.5 text-[0.6rem] text-muted-foreground/70 drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]">
  {#each items as item}
    <div class="flex items-center gap-1.5">
      <svg width="16" height="6" class="shrink-0">
        <line
          x1="0" y1="3" x2={item.arrow ? '11' : '16'} y2="3"
          stroke={item.color}
          stroke-width="1.5"
          stroke-dasharray={item.dasharray}
          stroke-linecap={item.linecap}
        />
        {#if item.arrow}
          <polygon points="11,0 16,3 11,6" fill={item.color} />
        {/if}
      </svg>
      <span>{item.label}</span>
    </div>
  {/each}
</div>
