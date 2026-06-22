<script lang="ts">
  import { page } from '$app/state';
</script>

<div class="flex min-h-screen items-center justify-center bg-[#0d1117] p-4 [background-image:linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] [background-size:60px_60px]">
  <div class="text-center font-mono">
    <p class="text-xs tracking-widest text-muted-foreground/50">GANG.GUIDE</p>
    <h1 class="mt-4 text-9xl font-black tracking-tighter font-sans text-foreground/90">{page.status}</h1>
    <p class="mt-3 text-sm text-muted-foreground">{page.error?.message ?? 'Something went wrong'}</p>
    <a
      href="/"
      class="mt-8 inline-block text-xs text-foreground/60 underline underline-offset-4 hover:text-foreground"
    >
      ← back to map
    </a>
  </div>
</div>
