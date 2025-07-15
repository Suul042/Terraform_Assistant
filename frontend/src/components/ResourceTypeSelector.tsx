/**
 * Resource Type Selector Component
 */
import { useState, useEffect, useMemo } from 'react';
import { MagnifyingGlassIcon, ServerIcon, FolderIcon } from '@heroicons/react/24/outline';
import { ResourceType } from '@/lib/api';
import { useResourceTypes, useSelectedResourceType, useAppActions } from '@/store/app';
import { clsx } from 'clsx';

interface ResourceTypeSelectorProps {
  onResourceTypeChange?: (resourceType: ResourceType) => void;
  disabled?: boolean;
}

export default function ResourceTypeSelector({ onResourceTypeChange, disabled = false }: ResourceTypeSelectorProps) {
  const resourceTypes = useResourceTypes();
  const selectedResourceType = useSelectedResourceType();
  const { setSelectedResourceType } = useAppActions();
  
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Filter and group resource types
  const { filteredTypes, categories } = useMemo(() => {
    const categories = new Set<string>();
    
    const filtered = resourceTypes.filter((type) => {
      categories.add(type.category || 'Other');
      
      const matchesSearch = !searchTerm || 
        type.resource_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        type.description?.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesCategory = selectedCategory === 'all' || 
        (type.category || 'Other') === selectedCategory;
      
      return matchesSearch && matchesCategory;
    });

    return {
      filteredTypes: filtered,
      categories: Array.from(categories).sort(),
    };
  }, [resourceTypes, searchTerm, selectedCategory]);

  const handleResourceTypeSelect = (resourceType: ResourceType) => {
    setSelectedResourceType(resourceType);
    onResourceTypeChange?.(resourceType);
  };

  const getResourceIcon = (resourceType: string) => {
    const iconMap: Record<string, string> = {
      instance: '🖥️',
      vpc: '🌐',
      subnet: '🔗',
      security_group: '🛡️',
      load_balancer: '⚖️',
      database: '🗄️',
      storage: '💾',
      lambda: '⚡',
      function: '⚡',
    };
    
    for (const [key, icon] of Object.entries(iconMap)) {
      if (resourceType.toLowerCase().includes(key)) {
        return icon;
      }
    }
    
    return '📦';
  };

  const getCategoryColor = (category: string) => {
    const colorMap: Record<string, string> = {
      Compute: 'bg-blue-100 text-blue-800',
      Network: 'bg-green-100 text-green-800',
      Storage: 'bg-purple-100 text-purple-800',
      Database: 'bg-orange-100 text-orange-800',
      Security: 'bg-red-100 text-red-800',
      Other: 'bg-gray-100 text-gray-800',
    };
    return colorMap[category] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className={clsx('w-full', disabled && 'opacity-50 pointer-events-none')}>
      {/* Search and Filter */}
      <div className="mb-4 space-y-3">
        {/* Search */}
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search resource types..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>

        {/* Category Filter */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedCategory('all')}
            className={clsx(
              'px-3 py-1 rounded-full text-sm font-medium transition-colors',
              selectedCategory === 'all'
                ? 'bg-primary-100 text-primary-800'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
          >
            All ({resourceTypes.length})
          </button>
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={clsx(
                'px-3 py-1 rounded-full text-sm font-medium transition-colors',
                selectedCategory === category
                  ? 'bg-primary-100 text-primary-800'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {category} ({resourceTypes.filter(t => (t.category || 'Other') === category).length})
            </button>
          ))}
        </div>
      </div>

      {/* Resource Types List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredTypes.length === 0 ? (
          <div className="text-center py-8">
            <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No resource types found</h3>
            <p className="mt-1 text-sm text-gray-500">
              Try adjusting your search or filter criteria.
            </p>
          </div>
        ) : (
          filteredTypes.map((resourceType) => (
            <div
              key={resourceType.id}
              onClick={() => handleResourceTypeSelect(resourceType)}
              className={clsx(
                'p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md',
                selectedResourceType?.id === resourceType.id
                  ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
                  : 'border-gray-200 hover:border-gray-300'
              )}
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <span className="text-xl">
                    {getResourceIcon(resourceType.resource_type)}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {resourceType.resource_type}
                    </h3>
                    <span
                      className={clsx(
                        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                        getCategoryColor(resourceType.category || 'Other')
                      )}
                    >
                      {resourceType.category || 'Other'}
                    </span>
                  </div>
                  {resourceType.description && (
                    <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                      {resourceType.description}
                    </p>
                  )}
                  {resourceType.subcategory && (
                    <p className="mt-1 text-xs text-gray-500">
                      {resourceType.subcategory}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Selected Resource Type Summary */}
      {selectedResourceType && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Selected Resource</h4>
          <div className="flex items-center space-x-3">
            <span className="text-lg">
              {getResourceIcon(selectedResourceType.resource_type)}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">
                {selectedResourceType.resource_type}
              </p>
              <p className="text-xs text-gray-500">
                {selectedResourceType.provider.display_name} • {selectedResourceType.category || 'Other'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Resource Type Card Component
export function ResourceTypeCard({ 
  resourceType, 
  selected, 
  onClick 
}: { 
  resourceType: ResourceType; 
  selected: boolean; 
  onClick: () => void; 
}) {
  const getResourceIcon = (resourceType: string) => {
    // Same icon logic as above
    return '📦';
  };

  const getCategoryColor = (category: string) => {
    // Same color logic as above
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div
      onClick={onClick}
      className={clsx(
        'p-4 rounded-lg border cursor-pointer transition-all hover:shadow-md',
        selected
          ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
          : 'border-gray-200 hover:border-gray-300'
      )}
    >
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <span className="text-xl">
            {getResourceIcon(resourceType.resource_type)}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-medium text-gray-900 truncate">
              {resourceType.resource_type}
            </h3>
            <span
              className={clsx(
                'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                getCategoryColor(resourceType.category || 'Other')
              )}
            >
              {resourceType.category || 'Other'}
            </span>
          </div>
          {resourceType.description && (
            <p className="mt-1 text-sm text-gray-600 line-clamp-2">
              {resourceType.description}
            </p>
          )}
          {resourceType.documentation_url && (
            <a
              href={resourceType.documentation_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 text-xs text-primary-600 hover:text-primary-800"
              onClick={(e) => e.stopPropagation()}
            >
              View Documentation →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}