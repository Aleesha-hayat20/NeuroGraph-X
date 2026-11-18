// A page for a module planned for FYP-II. It says what the module will show and that
// nothing is available yet. It makes no request to the API.
export default function PlannedPage({ title, module, children }) {
  return (
    <section>
      <h1>{title}</h1>
      <p>
        <strong>Planned for FYP-II.</strong> {module}
      </p>
      <p className="muted">{children}</p>
    </section>
  )
}