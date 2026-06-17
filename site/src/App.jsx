import Nav from './layout/Nav/Nav'
import Hero from './sections/Hero/Hero'
import Problem from './sections/Problem/Problem'
import Trajectories from './sections/Trajectories/Trajectories'
import Demo from './sections/Demo/Demo'
import Results from './sections/Results/Results'
import Footer from './layout/Footer/Footer'

export default function App() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Problem />
        <Trajectories />
        <Demo />
        <Results />
      </main>
      <Footer />
    </>
  )
}
