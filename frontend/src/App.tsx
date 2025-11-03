import "./App.css";
import Seat from "./components/Seat";
import Table from "./components/Table";

function App() {
  return (
    <Table>
      <Seat label="UTG" />
      <Seat label="HJ" />
      <Seat label="CO" />
      <Seat label="BTN" />
      <Seat label="SB" />
      <Seat label="BB" />
    </Table>
  );
}

export default App;
