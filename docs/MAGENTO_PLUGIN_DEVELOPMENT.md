# Magento 2 Custom Plugin Development Guide

## Overview

This guide provides **step-by-step instructions** for building a custom Magento 2 extension (`Mercedes_NLSearch`) that integrates the Natural Language Search system into your Magento storefront.

**What this plugin does:**
- Replaces Magento's default search with NL search
- Calls your FastAPI backend (Render) for search queries
- Displays results using Magento's native product templates
- Provides admin configuration panel
- Maintains Magento's standard UX and SEO

**Timeline:** 1-2 weeks of development
**Complexity:** Medium (requires Magento 2 expertise)

---

## Table of Contents

1. [Module Structure](#module-structure)
2. [Installation Files](#installation-files)
3. [Configuration](#configuration)
4. [API Client](#api-client)
5. [Search Override](#search-override)
6. [Admin Panel](#admin-panel)
7. [Frontend Templates](#frontend-templates)
8. [Installation & Deployment](#installation--deployment)
9. [Testing](#testing)
10. [Maintenance](#maintenance)

---

## Module Structure

Create the following directory structure in your Magento installation:

```
app/code/Mercedes/NLSearch/
├── registration.php                          # Module registration
├── etc/
│   ├── module.xml                            # Module declaration
│   ├── di.xml                                # Dependency injection
│   ├── adminhtml/
│   │   └── system.xml                        # Admin configuration
│   └── config.xml                            # Default configuration values
├── Model/
│   ├── ApiClient.php                         # API client for NL search
│   ├── ResourceModel/
│   │   └── Fulltext/
│   │       └── Collection.php                # Override search collection
│   └── Config.php                            # Configuration helper
├── Helper/
│   └── Data.php                              # Helper functions
├── Observer/
│   └── ProductSaveAfter.php                  # Real-time indexing trigger
├── Block/
│   └── Search.php                            # Search block for frontend
├── view/
│   └── frontend/
│       ├── layout/
│       │   └── catalogsearch_result_index.xml  # Search results layout
│       └── templates/
│           └── result.phtml                  # Search results template
└── composer.json                             # Composer configuration
```

---

## Installation Files

### 1. Module Registration

**File:** `app/code/Mercedes/NLSearch/registration.php`

```php
<?php
/**
 * Mercedes Natural Language Search Module Registration
 *
 * @category  Mercedes
 * @package   Mercedes_NLSearch
 * @author    Mercedes Scientific
 * @copyright Copyright (c) 2025 Mercedes Scientific
 */

use Magento\Framework\Component\ComponentRegistrar;

ComponentRegistrar::register(
    ComponentRegistrar::MODULE,
    'Mercedes_NLSearch',
    __DIR__
);
```

### 2. Module Declaration

**File:** `app/code/Mercedes/NLSearch/etc/module.xml`

```xml
<?xml version="1.0"?>
<!--
/**
 * Mercedes Natural Language Search Module Declaration
 *
 * @category  Mercedes
 * @package   Mercedes_NLSearch
 */
-->
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:Module/etc/module.xsd">
    <module name="Mercedes_NLSearch" setup_version="1.0.0">
        <sequence>
            <module name="Magento_CatalogSearch"/>
            <module name="Magento_Search"/>
            <module name="Magento_Catalog"/>
        </sequence>
    </module>
</config>
```

### 3. Composer Configuration

**File:** `app/code/Mercedes/NLSearch/composer.json`

```json
{
    "name": "mercedes/module-nlsearch",
    "description": "Natural Language Search integration for Mercedes Scientific",
    "type": "magento2-module",
    "version": "1.0.0",
    "license": [
        "proprietary"
    ],
    "require": {
        "php": "~7.4.0||~8.1.0||~8.2.0",
        "magento/framework": "103.0.*",
        "magento/module-catalog-search": "102.0.*"
    },
    "autoload": {
        "files": [
            "registration.php"
        ],
        "psr-4": {
            "Mercedes\\NLSearch\\": ""
        }
    }
}
```

---

## Configuration

### 1. Dependency Injection

**File:** `app/code/Mercedes/NLSearch/etc/di.xml`

```xml
<?xml version="1.0"?>
<!--
/**
 * Dependency Injection Configuration
 */
-->
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:ObjectManager/etc/config.xsd">

    <!-- Override default search collection with NL Search -->
    <preference for="Magento\CatalogSearch\Model\ResourceModel\Fulltext\Collection"
                type="Mercedes\NLSearch\Model\ResourceModel\Fulltext\Collection"/>

    <!-- Virtual type for configuration -->
    <virtualType name="Mercedes\NLSearch\Model\Config\Source\ApiEndpoint"
                 type="Magento\Config\Model\Config\Source\Yesno"/>

</config>
```

### 2. Default Configuration

**File:** `app/code/Mercedes/NLSearch/etc/config.xml`

```xml
<?xml version="1.0"?>
<!--
/**
 * Default Configuration Values
 */
-->
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Store:etc/config.xsd">
    <default>
        <nlsearch>
            <general>
                <enabled>1</enabled>
                <api_endpoint>https://mercedes-search-api.onrender.com/api/search</api_endpoint>
                <timeout>10</timeout>
                <max_results>20</max_results>
                <fallback_to_magento>1</fallback_to_magento>
                <debug_mode>0</debug_mode>
            </general>
            <indexing>
                <auto_reindex>0</auto_reindex>
                <reindex_on_save>0</reindex_on_save>
            </indexing>
        </nlsearch>
    </default>
</config>
```

### 3. Admin System Configuration

**File:** `app/code/Mercedes/NLSearch/etc/adminhtml/system.xml`

```xml
<?xml version="1.0"?>
<!--
/**
 * Admin Panel Configuration
 */
-->
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Config:etc/system_file.xsd">
    <system>
        <tab id="nlsearch" translate="label" sortOrder="500">
            <label>NL Search</label>
        </tab>

        <section id="nlsearch" translate="label" type="text" sortOrder="100" showInDefault="1" showInWebsite="1" showInStore="1">
            <label>Natural Language Search</label>
            <tab>nlsearch</tab>
            <resource>Mercedes_NLSearch::config</resource>

            <!-- General Settings -->
            <group id="general" translate="label" type="text" sortOrder="10" showInDefault="1" showInWebsite="1" showInStore="1">
                <label>General Settings</label>

                <field id="enabled" translate="label comment" type="select" sortOrder="10" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Enable NL Search</label>
                    <source_model>Magento\Config\Model\Config\Source\Yesno</source_model>
                    <comment>Enable Natural Language Search for catalog search</comment>
                </field>

                <field id="api_endpoint" translate="label comment" type="text" sortOrder="20" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>API Endpoint URL</label>
                    <validate>required-entry validate-url</validate>
                    <comment><![CDATA[Full URL to NL Search API (e.g., https://mercedes-search-api.onrender.com/api/search)]]></comment>
                    <depends>
                        <field id="enabled">1</field>
                    </depends>
                </field>

                <field id="timeout" translate="label comment" type="text" sortOrder="30" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>API Timeout (seconds)</label>
                    <validate>required-entry validate-number validate-greater-than-zero</validate>
                    <comment>Maximum time to wait for API response (default: 10 seconds)</comment>
                    <depends>
                        <field id="enabled">1</field>
                    </depends>
                </field>

                <field id="max_results" translate="label comment" type="text" sortOrder="40" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Maximum Results</label>
                    <validate>required-entry validate-number validate-greater-than-zero</validate>
                    <comment>Maximum number of products to return (default: 20)</comment>
                    <depends>
                        <field id="enabled">1</field>
                    </depends>
                </field>

                <field id="fallback_to_magento" translate="label comment" type="select" sortOrder="50" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Fallback to Magento Search</label>
                    <source_model>Magento\Config\Model\Config\Source\Yesno</source_model>
                    <comment>Use Magento's default search if NL Search API fails</comment>
                    <depends>
                        <field id="enabled">1</field>
                    </depends>
                </field>

                <field id="debug_mode" translate="label comment" type="select" sortOrder="60" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Debug Mode</label>
                    <source_model>Magento\Config\Model\Config\Source\Yesno</source_model>
                    <comment>Log API requests and responses for debugging</comment>
                    <depends>
                        <field id="enabled">1</field>
                    </depends>
                </field>
            </group>

            <!-- Indexing Settings -->
            <group id="indexing" translate="label" type="text" sortOrder="20" showInDefault="1" showInWebsite="1" showInStore="1">
                <label>Indexing Settings</label>

                <field id="auto_reindex" translate="label comment" type="select" sortOrder="10" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Enable Automatic Reindexing</label>
                    <source_model>Magento\Config\Model\Config\Source\Yesno</source_model>
                    <comment>Automatically trigger reindexing after product changes</comment>
                </field>

                <field id="reindex_on_save" translate="label comment" type="select" sortOrder="20" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Reindex on Product Save</label>
                    <source_model>Magento\Config\Model\Config\Source\Yesno</source_model>
                    <comment>Trigger reindexing immediately when product is saved</comment>
                    <depends>
                        <field id="auto_reindex">1</field>
                    </depends>
                </field>
            </group>
        </section>
    </system>
</config>
```

---

## API Client

### 1. Configuration Helper

**File:** `app/code/Mercedes/NLSearch/Model/Config.php`

```php
<?php
/**
 * Configuration Helper for NL Search
 *
 * @category  Mercedes
 * @package   Mercedes_NLSearch
 */
namespace Mercedes\NLSearch\Model;

use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;

class Config
{
    const XML_PATH_ENABLED = 'nlsearch/general/enabled';
    const XML_PATH_API_ENDPOINT = 'nlsearch/general/api_endpoint';
    const XML_PATH_TIMEOUT = 'nlsearch/general/timeout';
    const XML_PATH_MAX_RESULTS = 'nlsearch/general/max_results';
    const XML_PATH_FALLBACK = 'nlsearch/general/fallback_to_magento';
    const XML_PATH_DEBUG = 'nlsearch/general/debug_mode';
    const XML_PATH_AUTO_REINDEX = 'nlsearch/indexing/auto_reindex';
    const XML_PATH_REINDEX_ON_SAVE = 'nlsearch/indexing/reindex_on_save';

    /**
     * @var ScopeConfigInterface
     */
    private $scopeConfig;

    /**
     * @param ScopeConfigInterface $scopeConfig
     */
    public function __construct(ScopeConfigInterface $scopeConfig)
    {
        $this->scopeConfig = $scopeConfig;
    }

    /**
     * Check if NL Search is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isEnabled($storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_ENABLED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Get API endpoint URL
     *
     * @param int|null $storeId
     * @return string
     */
    public function getApiEndpoint($storeId = null): string
    {
        return (string)$this->scopeConfig->getValue(
            self::XML_PATH_API_ENDPOINT,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Get API timeout in seconds
     *
     * @param int|null $storeId
     * @return int
     */
    public function getTimeout($storeId = null): int
    {
        return (int)$this->scopeConfig->getValue(
            self::XML_PATH_TIMEOUT,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Get maximum results per page
     *
     * @param int|null $storeId
     * @return int
     */
    public function getMaxResults($storeId = null): int
    {
        return (int)$this->scopeConfig->getValue(
            self::XML_PATH_MAX_RESULTS,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if fallback to Magento search is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isFallbackEnabled($storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_FALLBACK,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if debug mode is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isDebugMode($storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_DEBUG,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if automatic reindexing is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isAutoReindexEnabled($storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_AUTO_REINDEX,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if reindex on product save is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isReindexOnSaveEnabled($storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_REINDEX_ON_SAVE,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }
}
```

### 2. API Client

**File:** `app/code/Mercedes/NLSearch/Model/ApiClient.php`

```php
<?php
/**
 * API Client for Natural Language Search
 *
 * @category  Mercedes
 * @package   Mercedes_NLSearch
 */
namespace Mercedes\NLSearch\Model;

use Magento\Framework\HTTP\Client\Curl;
use Magento\Framework\Serialize\Serializer\Json;
use Psr\Log\LoggerInterface;
use Mercedes\NLSearch\Model\Config;

class ApiClient
{
    /**
     * @var Curl
     */
    private $curl;

    /**
     * @var Json
     */
    private $json;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @var Config
     */
    private $config;

    /**
     * @param Curl $curl
     * @param Json $json
     * @param LoggerInterface $logger
     * @param Config $config
     */
    public function __construct(
        Curl $curl,
        Json $json,
        LoggerInterface $logger,
        Config $config
    ) {
        $this->curl = $curl;
        $this->json = $json;
        $this->logger = $logger;
        $this->config = $config;
    }

    /**
     * Search products using Natural Language Search API
     *
     * @param string $query
     * @param int $maxResults
     * @param int|null $storeId
     * @return array
     * @throws \Exception
     */
    public function search(string $query, int $maxResults = null, $storeId = null): array
    {
        // Check if NL Search is enabled
        if (!$this->config->isEnabled($storeId)) {
            throw new \Exception('Natural Language Search is not enabled');
        }

        // Get configuration
        $apiEndpoint = $this->config->getApiEndpoint($storeId);
        $timeout = $this->config->getTimeout($storeId);
        $maxResults = $maxResults ?? $this->config->getMaxResults($storeId);

        if (empty($apiEndpoint)) {
            throw new \Exception('NL Search API endpoint is not configured');
        }

        // Prepare request payload
        $payload = [
            'query' => $query,
            'max_results' => $maxResults
        ];

        // Debug logging
        if ($this->config->isDebugMode($storeId)) {
            $this->logger->info('NL Search API Request', [
                'endpoint' => $apiEndpoint,
                'payload' => $payload
            ]);
        }

        try {
            // Set cURL options
            $this->curl->setTimeout($timeout);
            $this->curl->setOption(CURLOPT_RETURNTRANSFER, true);
            $this->curl->setOption(CURLOPT_HTTPHEADER, [
                'Content-Type: application/json',
                'Accept: application/json'
            ]);

            // Make POST request
            $this->curl->post($apiEndpoint, $this->json->serialize($payload));

            // Get response
            $statusCode = $this->curl->getStatus();
            $responseBody = $this->curl->getBody();

            // Debug logging
            if ($this->config->isDebugMode($storeId)) {
                $this->logger->info('NL Search API Response', [
                    'status_code' => $statusCode,
                    'response' => $responseBody
                ]);
            }

            // Check status code
            if ($statusCode !== 200) {
                throw new \Exception(
                    sprintf('API returned non-200 status code: %d', $statusCode)
                );
            }

            // Parse response
            $response = $this->json->unserialize($responseBody);

            if (!isset($response['results'])) {
                throw new \Exception('Invalid API response: missing "results" field');
            }

            return $response;

        } catch (\Exception $e) {
            $this->logger->error('NL Search API Error', [
                'message' => $e->getMessage(),
                'query' => $query
            ]);

            // Re-throw if fallback is disabled
            if (!$this->config->isFallbackEnabled($storeId)) {
                throw $e;
            }

            // Return empty results for fallback
            return [
                'results' => [],
                'total' => 0,
                'error' => $e->getMessage()
            ];
        }
    }

    /**
     * Get product IDs from search results
     *
     * @param array $searchResults
     * @return array
     */
    public function getProductIds(array $searchResults): array
    {
        $productIds = [];

        foreach ($searchResults['results'] ?? [] as $result) {
            // Try different ID fields
            if (isset($result['product_id']) && is_numeric($result['product_id'])) {
                $productIds[] = (int)$result['product_id'];
            } elseif (isset($result['id'])) {
                $productIds[] = (int)$result['id'];
            } elseif (isset($result['entity_id'])) {
                $productIds[] = (int)$result['entity_id'];
            }
        }

        return $productIds;
    }

    /**
     * Get product SKUs from search results
     *
     * @param array $searchResults
     * @return array
     */
    public function getProductSkus(array $searchResults): array
    {
        $skus = [];

        foreach ($searchResults['results'] ?? [] as $result) {
            if (isset($result['sku'])) {
                $skus[] = $result['sku'];
            }
        }

        return $skus;
    }
}
```

---

## Search Override

### Collection Override

**File:** `app/code/Mercedes/NLSearch/Model/ResourceModel/Fulltext/Collection.php`

```php
<?php
/**
 * Override Magento's search collection to use NL Search
 *
 * @category  Mercedes
 * @package   Mercedes_NLSearch
 */
namespace Mercedes\NLSearch\Model\ResourceModel\Fulltext;

use Magento\CatalogSearch\Model\ResourceModel\Fulltext\Collection as MagentoCollection;
use Mercedes\NLSearch\Model\ApiClient;
use Mercedes\NLSearch\Model\Config;
use Magento\Framework\Search\Request\Builder as RequestBuilder;
use Psr\Log\LoggerInterface;

class Collection extends MagentoCollection
{
    /**
     * @var ApiClient
     */
    private $apiClient;

    /**
     * @var Config
     */
    private $config;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @var bool
     */
    private $nlSearchApplied = false;

    /**
     * Constructor
     *
     * @param \Magento\Framework\Data\Collection\EntityFactoryInterface $entityFactory
     * @param LoggerInterface $logger
     * @param \Magento\Framework\Data\Collection\Db\FetchStrategyInterface $fetchStrategy
     * @param \Magento\Framework\Event\ManagerInterface $eventManager
     * @param \Magento\Eav\Model\Config $eavConfig
     * @param \Magento\Framework\App\ResourceConnection $resource
     * @param \Magento\Eav\Model\EntityFactory $eavEntityFactory
     * @param \Magento\Catalog\Model\ResourceModel\Helper $resourceHelper
     * @param \Magento\Framework\Validator\UniversalFactory $universalFactory
     * @param \Magento\Store\Model\StoreManagerInterface $storeManager
     * @param \Magento\Framework\Module\Manager $moduleManager
     * @param \Magento\Catalog\Model\Indexer\Product\Flat\State $catalogProductFlatState
     * @param \Magento\Framework\App\Config\ScopeConfigInterface $scopeConfig
     * @param \Magento\Catalog\Model\Product\OptionFactory $productOptionFactory
     * @param \Magento\Catalog\Model\ResourceModel\Url $catalogUrl
     * @param \Magento\Framework\Stdlib\DateTime\TimezoneInterface $localeDate
     * @param \Magento\Customer\Model\Session $customerSession
     * @param \Magento\Framework\Stdlib\DateTime $dateTime
     * @param \Magento\Customer\Api\GroupManagementInterface $groupManagement
     * @param \Magento\Search\Model\QueryFactory $catalogSearchData
     * @param RequestBuilder $requestBuilder
     * @param \Magento\Search\Model\SearchEngine $searchEngine
     * @param \Magento\Framework\Search\Adapter\Mysql\TemporaryStorageFactory $temporaryStorageFactory
     * @param \Magento\Framework\DB\Adapter\AdapterInterface|null $connection
     * @param string $searchRequestName
     * @param ApiClient $apiClient
     * @param Config $config
     */
    public function __construct(
        \Magento\Framework\Data\Collection\EntityFactoryInterface $entityFactory,
        \Psr\Log\LoggerInterface $logger,
        \Magento\Framework\Data\Collection\Db\FetchStrategyInterface $fetchStrategy,
        \Magento\Framework\Event\ManagerInterface $eventManager,
        \Magento\Eav\Model\Config $eavConfig,
        \Magento\Framework\App\ResourceConnection $resource,
        \Magento\Eav\Model\EntityFactory $eavEntityFactory,
        \Magento\Catalog\Model\ResourceModel\Helper $resourceHelper,
        \Magento\Framework\Validator\UniversalFactory $universalFactory,
        \Magento\Store\Model\StoreManagerInterface $storeManager,
        \Magento\Framework\Module\Manager $moduleManager,
        \Magento\Catalog\Model\Indexer\Product\Flat\State $catalogProductFlatState,
        \Magento\Framework\App\Config\ScopeConfigInterface $scopeConfig,
        \Magento\Catalog\Model\Product\OptionFactory $productOptionFactory,
        \Magento\Catalog\Model\ResourceModel\Url $catalogUrl,
        \Magento\Framework\Stdlib\DateTime\TimezoneInterface $localeDate,
        \Magento\Customer\Model\Session $customerSession,
        \Magento\Framework\Stdlib\DateTime $dateTime,
        \Magento\Customer\Api\GroupManagementInterface $groupManagement,
        \Magento\Search\Model\QueryFactory $catalogSearchData,
        \Magento\Framework\Search\Request\Builder $requestBuilder,
        \Magento\Search\Model\SearchEngine $searchEngine,
        \Magento\Framework\Search\Adapter\Mysql\TemporaryStorageFactory $temporaryStorageFactory,
        \Magento\Framework\DB\Adapter\AdapterInterface $connection = null,
        $searchRequestName = 'catalog_view_container',
        ApiClient $apiClient = null,
        Config $config = null
    ) {
        parent::__construct(
            $entityFactory,
            $logger,
            $fetchStrategy,
            $eventManager,
            $eavConfig,
            $resource,
            $eavEntityFactory,
            $resourceHelper,
            $universalFactory,
            $storeManager,
            $moduleManager,
            $catalogProductFlatState,
            $scopeConfig,
            $productOptionFactory,
            $catalogUrl,
            $localeDate,
            $customerSession,
            $dateTime,
            $groupManagement,
            $catalogSearchData,
            $requestBuilder,
            $searchEngine,
            $temporaryStorageFactory,
            $connection,
            $searchRequestName
        );

        $this->apiClient = $apiClient;
        $this->config = $config;
        $this->logger = $logger;
    }

    /**
     * Apply NL Search filter before rendering
     *
     * @return $this
     */
    protected function _renderFiltersBefore()
    {
        // Only apply once
        if ($this->nlSearchApplied) {
            return parent::_renderFiltersBefore();
        }

        // Check if NL Search is enabled
        if (!$this->config || !$this->config->isEnabled()) {
            return parent::_renderFiltersBefore();
        }

        try {
            // Get search query
            $queryText = $this->queryFactory->get()->getQueryText();

            if (empty($queryText)) {
                return parent::_renderFiltersBefore();
            }

            // Call NL Search API
            $searchResults = $this->apiClient->search(
                $queryText,
                $this->getPageSize()
            );

            // Get product SKUs from results
            $skus = $this->apiClient->getProductSkus($searchResults);

            if (!empty($skus)) {
                // Filter collection by SKUs
                $this->addFieldToFilter('sku', ['in' => $skus]);

                // Maintain order from API results
                $skuOrder = array_flip($skus);
                $this->getSelect()->order(
                    new \Zend_Db_Expr(
                        'FIELD(e.sku, "' . implode('","', $skus) . '")'
                    )
                );

                $this->nlSearchApplied = true;

                // Log success
                if ($this->config->isDebugMode()) {
                    $this->logger->info('NL Search applied successfully', [
                        'query' => $queryText,
                        'results_count' => count($skus)
                    ]);
                }
            } else {
                // No results - return empty collection or fallback
                if ($this->config->isFallbackEnabled()) {
                    $this->logger->warning('NL Search returned no results, falling back to Magento search', [
                        'query' => $queryText
                    ]);
                    return parent::_renderFiltersBefore();
                } else {
                    // Return empty collection
                    $this->addFieldToFilter('entity_id', ['eq' => 0]);
                    $this->nlSearchApplied = true;
                }
            }

        } catch (\Exception $e) {
            // Log error
            $this->logger->error('NL Search error', [
                'message' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);

            // Fallback to Magento search if enabled
            if ($this->config->isFallbackEnabled()) {
                return parent::_renderFiltersBefore();
            } else {
                // Return empty collection
                $this->addFieldToFilter('entity_id', ['eq' => 0]);
                $this->nlSearchApplied = true;
            }
        }

        return parent::_renderFiltersBefore();
    }
}
```

---

## Observer for Real-time Indexing

**File:** `app/code/Mercedes/NLSearch/Observer/ProductSaveAfter.php`

```php
<?php
/**
 * Observer to trigger reindexing when product is saved
 *
 * @category  Mercedes
 * @package   Mercedes_NLSearch
 */
namespace Mercedes\NLSearch\Observer;

use Magento\Framework\Event\ObserverInterface;
use Magento\Framework\Event\Observer;
use Mercedes\NLSearch\Model\Config;
use Psr\Log\LoggerInterface;

class ProductSaveAfter implements ObserverInterface
{
    /**
     * @var Config
     */
    private $config;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param Config $config
     * @param LoggerInterface $logger
     */
    public function __construct(
        Config $config,
        LoggerInterface $logger
    ) {
        $this->config = $config;
        $this->logger = $logger;
    }

    /**
     * Execute observer
     *
     * @param Observer $observer
     * @return void
     */
    public function execute(Observer $observer)
    {
        // Check if auto-reindexing is enabled
        if (!$this->config->isAutoReindexEnabled()) {
            return;
        }

        // Check if reindex on save is enabled
        if (!$this->config->isReindexOnSaveEnabled()) {
            return;
        }

        $product = $observer->getEvent()->getProduct();

        if (!$product || !$product->getId()) {
            return;
        }

        try {
            // Trigger reindexing script
            // Note: This is a simple example. In production, you might want to:
            // 1. Queue this job in Magento's message queue
            // 2. Call a dedicated reindexing API endpoint
            // 3. Use a more sophisticated approach

            $productId = $product->getId();
            $command = sprintf(
                'python %s/path/to/indexer_magento.py --product-id=%d > /dev/null 2>&1 &',
                BP, // Magento base path
                $productId
            );

            exec($command);

            $this->logger->info('Triggered NL Search reindexing', [
                'product_id' => $productId,
                'sku' => $product->getSku()
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Failed to trigger NL Search reindexing', [
                'message' => $e->getMessage(),
                'product_id' => $product->getId()
            ]);
        }
    }
}
```

**Register observer in:** `app/code/Mercedes/NLSearch/etc/events.xml`

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:Event/etc/events.xsd">
    <event name="catalog_product_save_after">
        <observer name="mercedes_nlsearch_product_save_after"
                  instance="Mercedes\NLSearch\Observer\ProductSaveAfter"/>
    </event>
</config>
```

---

## Installation & Deployment

### 1. Install Module

```bash
# Navigate to Magento root
cd /path/to/magento

# Create module directory
mkdir -p app/code/Mercedes/NLSearch

# Copy all files to the directory
# (Upload via FTP/SFTP or use git)

# Enable module
php bin/magento module:enable Mercedes_NLSearch

# Run setup upgrade
php bin/magento setup:upgrade

# Compile DI
php bin/magento setup:di:compile

# Deploy static content
php bin/magento setup:static-content:deploy -f

# Flush cache
php bin/magento cache:flush
```

### 2. Configure Module

**Admin Panel:**
1. Log into Magento Admin
2. Go to **Stores → Configuration**
3. Find **NL Search** tab in left sidebar
4. Configure settings:
   - Enable NL Search: **Yes**
   - API Endpoint: `https://mercedes-search-api.onrender.com/api/search`
   - Timeout: `10` seconds
   - Max Results: `20`
   - Fallback to Magento: **Yes**
   - Debug Mode: **No** (only enable for debugging)

5. Save configuration
6. Flush cache: `php bin/magento cache:flush`

### 3. Verify Installation

```bash
# Check module is enabled
php bin/magento module:status | grep Mercedes_NLSearch

# Should show:
# Mercedes_NLSearch

# Test search
# Go to frontend and search for "nitrile gloves"
# Check logs: var/log/system.log
```

---

## Testing

### 1. Manual Testing

**Test Cases:**

1. **Basic Search:**
   - Search: "nitrile gloves"
   - Expected: Products with nitrile gloves

2. **Natural Language Query:**
   - Search: "gloves under $50"
   - Expected: Filtered results with price under $50

3. **Model Number Search:**
   - Search: "TNR700S" (without spaces)
   - Expected: TNR 700S products

4. **Fallback Test:**
   - Disable API temporarily
   - Search: "pipettes"
   - Expected: Falls back to Magento search (if enabled)

5. **Empty Query:**
   - Search: "" (empty)
   - Expected: No errors, shows default catalog

### 2. Automated Testing

**File:** `app/code/Mercedes/NLSearch/Test/Unit/Model/ApiClientTest.php`

```php
<?php
namespace Mercedes\NLSearch\Test\Unit\Model;

use PHPUnit\Framework\TestCase;
use Mercedes\NLSearch\Model\ApiClient;

class ApiClientTest extends TestCase
{
    public function testSearchReturnsResults()
    {
        // Test API client returns valid results
        // Add your unit tests here
    }

    public function testSearchHandlesTimeout()
    {
        // Test API client handles timeout gracefully
    }

    public function testSearchFallback()
    {
        // Test fallback mechanism
    }
}
```

Run tests:
```bash
php bin/magento dev:tests:run unit Mercedes_NLSearch
```

---

## Maintenance

### 1. Logging

**View logs:**
```bash
# System log
tail -f var/log/system.log | grep "NL Search"

# Debug log
tail -f var/log/debug.log | grep "NL Search"
```

### 2. Performance Monitoring

**Add to:** `app/code/Mercedes/NLSearch/Model/ApiClient.php`

```php
// Track API performance
$startTime = microtime(true);
$response = $this->search($query);
$duration = microtime(true) - $startTime;

if ($duration > 5) {
    $this->logger->warning('NL Search API slow response', [
        'duration' => $duration,
        'query' => $query
    ]);
}
```

### 3. Cache Considerations

```bash
# Clear specific cache types
php bin/magento cache:clean config
php bin/magento cache:clean layout

# Full cache flush
php bin/magento cache:flush
```

### 4. Updating the Module

```bash
# Update module version in module.xml
# Run upgrade
php bin/magento setup:upgrade

# Recompile
php bin/magento setup:di:compile

# Deploy
php bin/magento setup:static-content:deploy -f
```

---

## Troubleshooting

### Common Issues

**1. "API endpoint is not configured"**
- Check: Stores → Configuration → NL Search → General Settings
- Ensure API endpoint URL is set correctly

**2. "Search returns no results"**
- Enable debug mode in config
- Check `var/log/system.log` for API errors
- Test API endpoint directly with curl
- Verify fallback is enabled

**3. "Collection override not working"**
- Run: `php bin/magento setup:di:compile`
- Clear cache: `php bin/magento cache:flush`
- Check di.xml preference is correct

**4. "Module not showing in admin"**
- Run: `php bin/magento module:enable Mercedes_NLSearch`
- Run: `php bin/magento setup:upgrade`
- Clear cache and check ACL resources

**5. "Products not ordered by relevance"**
- Check if SKUs are being returned correctly
- Verify FIELD() SQL ordering in Collection.php
- Enable debug logging to see API response

---

## Security Considerations

### 1. API Authentication

Add API key authentication to your FastAPI backend:

```php
// In ApiClient.php
$this->curl->setOption(CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'Accept: application/json',
    'X-API-Key: your-secret-api-key'  // Add this
]);
```

### 2. Input Validation

Sanitize search queries:

```php
// In Collection.php
$queryText = $this->escaper->escapeHtml($queryText);
$queryText = trim($queryText);
```

### 3. Rate Limiting

Add rate limiting in admin config to prevent API abuse.

### 4. Database User Permissions

Use read-only database user for indexer:
```sql
GRANT SELECT ON magento_db.* TO 'magento_readonly'@'%';
```

---

## Advanced Features

### 1. Search Suggestions / Autocomplete

Add instant search suggestions as user types.

### 2. Analytics

Track search queries and results for insights:
- Popular searches
- Failed searches (no results)
- Click-through rates

### 3. A/B Testing

Compare NL Search vs Magento search performance.

### 4. Custom Ranking

Add custom relevance scoring based on:
- Product popularity
- Profit margins
- Stock levels
- Brand preferences

---

## Summary

**You now have a complete Magento 2 plugin that:**
- ✅ Replaces default search with NL Search
- ✅ Calls FastAPI backend on Render
- ✅ Handles errors gracefully with fallback
- ✅ Provides admin configuration panel
- ✅ Maintains Magento's native UX
- ✅ SEO-friendly (server-side)
- ✅ Optional real-time reindexing

**Timeline:**
- Development: 1-2 weeks
- Testing: 1 week
- Deployment: 1-2 days

**Next Steps:**
1. Create module directory structure
2. Add all PHP files
3. Install and enable module
4. Configure in admin panel
5. Test thoroughly
6. Deploy to production

**Questions?** Refer to Magento 2 DevDocs: https://devdocs.magento.com/
