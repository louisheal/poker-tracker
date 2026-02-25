import "./App.css";

import { ThemeProvider } from "@/components/theme-provider";
import { RangeView } from "./views/RangeView";

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <RangeView />
    </ThemeProvider>
  );
}

export default App;
