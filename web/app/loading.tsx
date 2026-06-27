export default function Loading() {
  return (
    <main className="shell" aria-busy="true">
      <header className="topbar">
        <div>
          <h1>Rory TradeR</h1>
          <p>Tennis Betfair paper monitor</p>
        </div>
        <div className="status-row">
          <span className="pill warn">Loading</span>
        </div>
      </header>

      <section className="loading-grid" aria-label="Loading dashboard">
        <div />
        <div />
        <div />
        <div />
      </section>
      <section className="panel loading-panel" />
      <section className="cockpit-grid">
        <section className="panel loading-panel" />
        <section className="panel loading-panel" />
      </section>
    </main>
  );
}
