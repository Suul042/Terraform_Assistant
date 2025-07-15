/**
 * Provider Selector Component
 */
import { useState, useEffect } from 'react';
import { ChevronDownIcon, CloudIcon, CheckIcon } from '@heroicons/react/24/outline';
import { Listbox, Transition } from '@headlessui/react';
import { CloudProvider } from '@/lib/api';
import { useSelectedProvider, useProviders, useAppActions } from '@/store/app';
import { clsx } from 'clsx';

interface ProviderSelectorProps {
  onProviderChange?: (provider: CloudProvider) => void;
  disabled?: boolean;
}

export default function ProviderSelector({ onProviderChange, disabled = false }: ProviderSelectorProps) {
  const providers = useProviders();
  const selectedProvider = useSelectedProvider();
  const { setSelectedProvider } = useAppActions();

  const handleProviderChange = (provider: CloudProvider) => {
    setSelectedProvider(provider);
    onProviderChange?.(provider);
  };

  const getProviderIcon = (providerName: string) => {
    const iconMap: Record<string, string> = {
      aws: '🟧',
      azure: '🔵',
      gcp: '🟢',
    };
    return iconMap[providerName] || '☁️';
  };

  const getProviderColor = (providerName: string) => {
    const colorMap: Record<string, string> = {
      aws: 'bg-orange-100 text-orange-800 border-orange-200',
      azure: 'bg-blue-100 text-blue-800 border-blue-200',
      gcp: 'bg-green-100 text-green-800 border-green-200',
    };
    return colorMap[providerName] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  return (
    <div className="w-full">
      <Listbox value={selectedProvider} onChange={handleProviderChange} disabled={disabled}>
        <div className="relative">
          <Listbox.Button
            className={clsx(
              'relative w-full cursor-default rounded-lg border py-2 pl-3 pr-10 text-left shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500',
              disabled
                ? 'bg-gray-50 border-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-white border-gray-300 text-gray-900 hover:border-gray-400'
            )}
          >
            <div className="flex items-center">
              {selectedProvider ? (
                <>
                  <span className="text-lg mr-2">
                    {getProviderIcon(selectedProvider.name)}
                  </span>
                  <span className="block truncate font-medium">
                    {selectedProvider.display_name}
                  </span>
                  <span
                    className={clsx(
                      'ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
                      getProviderColor(selectedProvider.name)
                    )}
                  >
                    {selectedProvider.sync_status}
                  </span>
                </>
              ) : (
                <>
                  <CloudIcon className="h-5 w-5 text-gray-400 mr-2" />
                  <span className="block truncate text-gray-500">Select a cloud provider</span>
                </>
              )}
            </div>
            <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              <ChevronDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
            </span>
          </Listbox.Button>

          <Transition
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
              {providers.map((provider) => (
                <Listbox.Option
                  key={provider.id}
                  className={({ active }) =>
                    clsx(
                      'relative cursor-default select-none py-2 pl-3 pr-9',
                      active ? 'bg-primary-100 text-primary-900' : 'text-gray-900'
                    )
                  }
                  value={provider}
                >
                  {({ selected, active }) => (
                    <>
                      <div className="flex items-center">
                        <span className="text-lg mr-2">
                          {getProviderIcon(provider.name)}
                        </span>
                        <div className="flex-1 min-w-0">
                          <span
                            className={clsx(
                              'block truncate font-medium',
                              selected ? 'font-semibold' : 'font-normal'
                            )}
                          >
                            {provider.display_name}
                          </span>
                          {provider.documentation_base_url && (
                            <span className="text-xs text-gray-500 truncate block">
                              {provider.documentation_base_url}
                            </span>
                          )}
                        </div>
                        <span
                          className={clsx(
                            'ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
                            getProviderColor(provider.name)
                          )}
                        >
                          {provider.sync_status}
                        </span>
                      </div>

                      {selected && (
                        <span
                          className={clsx(
                            'absolute inset-y-0 right-0 flex items-center pr-4',
                            active ? 'text-primary-600' : 'text-primary-600'
                          )}
                        >
                          <CheckIcon className="h-5 w-5" aria-hidden="true" />
                        </span>
                      )}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
    </div>
  );
}

// Provider Status Badge Component
export function ProviderStatusBadge({ status }: { status: string }) {
  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      active: 'bg-green-100 text-green-800 border-green-200',
      syncing: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      error: 'bg-red-100 text-red-800 border-red-200',
      disabled: 'bg-gray-100 text-gray-800 border-gray-200',
    };
    return colorMap[status] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
        getStatusColor(status)
      )}
    >
      {status}
    </span>
  );
}