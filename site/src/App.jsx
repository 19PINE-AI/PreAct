import Nav from './components/Nav'
import Hero from './components/Hero'
import Problem from './components/Problem'
import Architecture from './components/Architecture'
import Demo from './components/Demo'
import Corpus from './components/Corpus'
import Trajectories from './components/Trajectories'
import Results from './components/Results'
import Footer from './components/Footer'

export default function App() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Problem />
        <Architecture />
        <Demo />
        <Corpus />
        <Trajectories />
        <Results />
      </main>
      <Footer />
    </>
  )
}
