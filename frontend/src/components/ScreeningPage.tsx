/**
 * ScreeningPage — Single entry component for the Screening page.
 * 
 * Decides whether to render ScreeningSetup or ScreeningSession
 * based on URL parameters.
 */

import ScreeningSetup from "./ScreeningSetup";
import ScreeningSessionView from "./ScreeningSession";

export default function ScreeningPage() {
    const params = new URLSearchParams(window.location.search);
    const hasSession = params.has("session");

    if (hasSession) {
        return <ScreeningSessionView />;
    }

    return <ScreeningSetup />;
}
