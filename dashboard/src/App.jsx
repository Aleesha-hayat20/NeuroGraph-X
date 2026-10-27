import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import About from './pages/About.jsx'
import Analysis from './pages/Analysis.jsx'
import Exclusions from './pages/Exclusions.jsx'
import History from './pages/History.jsx'
import Models from './pages/Models.jsx'
import Overview from './pages/Overview.jsx'
import Participants from './pages/Participants.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="participants" element={<Participants />} />
        <Route path="analysis" element={<Analysis />} />
        <Route path="history" element={<History />} />
        <Route path="models" element={<Models />} />
        <Route path="exclusions" element={<Exclusions />} />
        <Route path="about" element={<About />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

function NotFound() {
  return (
    <section>
      <h1>Page not found</h1>
      <p className="muted">Use the menu above to open one of the seven pages.</p>
    </section>
  )
}
