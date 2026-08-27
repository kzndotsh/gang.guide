import { MediaQuery } from "svelte/reactivity";

const DEFAULT_MOBILE_BREAKPOINT = 768;

export class IsMobile extends MediaQuery {
	constructor(breakpoint: number = DEFAULT_MOBILE_BREAKPOINT) {
		// SSR/prerender has no viewport — default true (mobile) so phones don't
		// flash the desktop PaneGroup inspector before hydration.
		super(`max-width: ${breakpoint - 1}px`, true);
	}
}
