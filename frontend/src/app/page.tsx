'use client'

import { useState } from 'react'

export default function Home() {
  const [provider, setProvider] = useState('aws')
  const [resourceType, setResourceType] = useState('')
  const [description, setDescription] = useState('')
  const [generatedCode, setGeneratedCode] = useState('')
  const [loading, setLoading] = useState(false)

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/generate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          resource_type: resourceType,
          description,
          parameters: {}
        }),
      })

      const data = await response.json()
      setGeneratedCode(data.code || JSON.stringify(data, null, 2))
    } catch (error) {
      console.error('Error generating code:', error)
      setGeneratedCode('Error generating code. Please check your configuration.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          Terraform Assistant
        </h1>
        <p className="text-gray-600 mb-8">
          AI-powered Terraform code generation and management
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Panel */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-2xl font-semibold mb-4">Generate Code</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cloud Provider
                </label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="aws">AWS</option>
                  <option value="azure">Azure</option>
                  <option value="gcp">Google Cloud</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Resource Type
                </label>
                <input
                  type="text"
                  value={resourceType}
                  onChange={(e) => setResourceType(e.target.value)}
                  placeholder="e.g., aws_instance, azurerm_virtual_machine"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description (Optional)
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe what you want to create..."
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={loading || !resourceType}
                className="w-full bg-blue-600 text-white font-medium py-3 px-6 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Generating...' : 'Generate Code'}
              </button>
            </div>
          </div>

          {/* Output Panel */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-2xl font-semibold mb-4">Generated Code</h2>

            {generatedCode ? (
              <div className="relative">
                <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
                  <code>{generatedCode}</code>
                </pre>
                <button
                  onClick={() => navigator.clipboard.writeText(generatedCode)}
                  className="absolute top-2 right-2 bg-gray-700 text-white px-3 py-1 rounded text-sm hover:bg-gray-600"
                >
                  Copy
                </button>
              </div>
            ) : (
              <div className="bg-gray-100 rounded-lg p-8 text-center text-gray-500">
                Generated code will appear here
              </div>
            )}
          </div>
        </div>

        {/* Features */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-2">AI-Powered</h3>
            <p className="text-gray-600">
              Leverage GPT-4 to generate optimized Terraform code with best practices.
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-2">Multi-Cloud</h3>
            <p className="text-gray-600">
              Support for AWS, Azure, and Google Cloud Platform out of the box.
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-2">Validation</h3>
            <p className="text-gray-600">
              Real-time code validation and syntax checking to ensure quality.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
