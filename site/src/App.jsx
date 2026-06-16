import Nav from './components/Nav'
import Hero from './components/Hero'
import Problem from './components/Problem'
import Architecture from './components/Architecture'
import Demo from './components/Demo'
import Corpus from './components/Corpus'
import Implementation from './components/Implementation'
import Benchmarks from './components/Benchmarks'
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
        <Implementation />
        <Benchmarks />
        <Results />
      </main>
      <Footer />
    </>
  )
}
