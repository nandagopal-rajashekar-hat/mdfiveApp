import { Route, Routes } from 'react-router-dom'
import LoadPage from './components/LoadPage'
import Dashboard from './components/Dashboard'
import Process_Reports from './components/Process_Reports';
import ReportComparison from './components/ReportComparison';
import SignIn from './components/Automation/SignIn';
import AutomationFolder from './components/Automation/Folder';
import SignUp from './components/Automation/SignUp';
import Forgot from './components/Automation/Forgot';


const App = () => {
  return (
    <Routes>
      <Route path="/" element={<LoadPage />} />
      <Route path="/automation" element={<AutomationFolder />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/processed_reports" element={<Process_Reports />} />
      <Route path="/ReportComparison" element={<ReportComparison />} />
      <Route path="/automation/signin" element={<SignIn />} />
      <Route path="/automation/signup" element={<SignUp />} />
      <Route path="/automation/forgot" element={<Forgot />} />
    </Routes>
  )
}

export default App
