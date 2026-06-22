<script lang="ts">
  /**
   * OrgSearch — command palette dialog (⌘K to open).
   */
  import * as Command from '$lib/components/ui/command/index.js';
  import { Search } from '@lucide/svelte';
  import type { Graph } from '$lib/types';
  import { searchOrgNodes } from '$lib/searchNodes';
  import { orgDisplayTitle } from '$lib/inspector/inspectorDisplay';

  interface Props {
    graph: Graph;
    onselect: (id: string) => void;
  }

  let { graph, onselect }: Props = $props();

  let open = $state(false);
  let query = $state('');

  const results = $derived(searchOrgNodes(graph.nodes, query, 12));

  export function focusSearch() {
    open = true;
  }

  function pick(id: string) {
    onselect(id);
    query = '';
    open = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      open = !open;
    }
  }
</script>

<svelte:document onkeydown={handleKeydown} />

<Command.Dialog bind:open class="sm:max-w-xl">
  <Command.Input placeholder="Search orgs..." bind:value={query} class="text-sm" />
  <Command.List>
    {#if query.length > 1}
      {#if results.length === 0}
        <Command.Empty>No results found.</Command.Empty>
      {:else}
        <Command.Group heading="Organizations">
          {#each results as result (result.node.id)}
            <Command.Item
              value={result.node.id}
              onSelect={() => pick(result.node.id)}
              class="text-xs"
            >
              <Search />
              <span>{orgDisplayTitle(result.node)}</span>
              {#if result.node.data?.metro}
                <Command.Shortcut>{result.node.data.metro}</Command.Shortcut>
              {/if}
            </Command.Item>
          {/each}
        </Command.Group>
      {/if}
    {:else}
      <Command.Empty class="text-xs">Type to search {graph.nodes.length} organizations...</Command.Empty>
    {/if}
  </Command.List>
</Command.Dialog>
