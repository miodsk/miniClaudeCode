import { createRoot } from 'react-dom/client'
import 'normalize.css'
import './index.css'
import { TooltipProvider } from "@/components/ui/tooltip"
import { RouterProvider } from 'react-router';
import {router} from './router';
const App= () => {
  return (
    <>
      <RouterProvider router={router} />
    </>
  );
}


createRoot(document.getElementById('root')!).render(
    <TooltipProvider>
        <App />
    </TooltipProvider>
)
export default App;
