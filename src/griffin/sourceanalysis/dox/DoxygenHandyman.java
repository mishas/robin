package sourceanalysis.dox;

import java.util.Collection;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.TreeNode;

import backend.Utils;

import sourceanalysis.*;

/**
 * Commits repairments to a Program Database generated by the DoxygenAnalyzer.
 * Some elements may be missing and some inconsistencies introduced as a
 * result of bugs and mis-features in Doxygen.
 * <p>This class is an implementation work-around. It should not be considered
 * a design issue.</p>
 */
public class DoxygenHandyman {

	/**
	 * Commences the repair of entities where cross-references between entities
	 * are broken. Transformation is accomplished by searching the map of
	 * recognized entities using the name of the base entity.
	 * Only leaf nodes (TypeNode.NODE_LEAF) are transformed by this functor.
	 */
	private class OrphanTypeRepair implements Type.Transformation
	{
		private Entity origin;
		
		public OrphanTypeRepair()
		{
			origin = null;
		}
		
		/**
		 * 
		 * @param origin location in the program to commence lookup at
		 */
		public OrphanTypeRepair(Entity origin)
		{
			this.origin = origin;
		}
		
		public Type.TypeNode transform(Type.TypeNode original)
			throws InappropriateKindException
		{
			if (original.getKind() != Type.TypeNode.NODE_LEAF)
                return null;

            if (original.getBase().hasContainer())
                return null;

            // If base is orphan, look it up
            Entity newBase = (origin == null) 
                    ? lookupApprox(original.getBase().getName())
                    : lookup(origin, original.getBase().getName());

            if (newBase == null)
                return null;

            // Create a new type node with 'base'
            Type.TypeNode transformed = new Type.TypeNode(original.getBase());
            transformed.setCV(original.getCV());
            return transformed;
		}
	}
	
	
	
	/**
	 * Constructor for DoxygenHandyman.
	 */
	public DoxygenHandyman(ProgramDatabase p) {
		super();
		m_program = p;
		m_entitiesByName = new HashMap();
		m_entitiesByFullName = new HashMap();
		collectEntitiesByName(p.getGlobalNamespace().getScope());
	}

	/**
	 * Creates two big maps that associate names to their
	 * entities.
	 * @param anchor a scope to start scanning from
	 */
	private void collectEntitiesByName(Scope anchor)
	{
		// Go through the aggregates
		for (Iterator aggiter = anchor.aggregateIterator(); aggiter.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)aggiter.next();
			collectContained(connection);
			// - descend
			Aggregate aggregate = (Aggregate)connection.getContained();
			collectEntitiesByName(aggregate.getScope());
		}
		// Go through aliases
		for (Iterator aliasiter = anchor.aliasIterator(); aliasiter.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)aliasiter.next();
			collectContained(connection);
		}
		// Go through enumerated types
		for (Iterator enumiter = anchor.enumIterator(); enumiter.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)enumiter.next();
			collectContained(connection);
		}
		// Even go through constant data members
		for (Iterator fielditer = anchor.fieldIterator(); fielditer.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)fielditer.next();
			Field field = (Field)connection.getContained();
			try {
				Type type = field.getType();
				if (type.isFlat() && type.isConst() 
						&& type.getBaseType() instanceof Primitive)
					collectContained(connection);
			}
			catch (MissingInformationException e) {
				// Fields with no type are ignored
			}
		}
		// Look in inner namespace scopes
		for (Iterator nsiter = anchor.namespaceIterator(); nsiter.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)nsiter.next();
			// - descend
			Namespace namespace = (Namespace)connection.getContained();
			collectEntitiesByName(namespace.getScope());
		}		
	}
	
	/**
	 * Inserts a single entity to both maps using a ContainedConnection.
	 * @param connection a ContainedConnection pointing to current entity
	 */
	private void collectContained(ContainedConnection connection)
	{
		Entity inside = connection.getContained();
		m_entitiesByName.put(inside.getName(), inside);
		m_entitiesByFullName.put(inside.getFullName(), inside);
	}
	
	/**
	 * Examines type, checking if there is a reason to suspect that type as
	 * one that requires repair. A type may require repair if any of the base
	 * entities involved are "hanging", that is, have no container. Since all
	 * the entities in the program database are contained in the global
	 * namespace, at least, entity name might have to be resolved.
	 * @param typeRoot root node of type tree or sub-tree
	 * @return boolean <b>true</b> for suspicious types
	 */
	private boolean isSuspicious(Type.TypeNode typeRoot)
	{
		if (typeRoot.getKind() == Type.TypeNode.NODE_LEAF) {
			// Return 'true' if base type is hanging
			try {
				return (typeRoot.getBase().getContainerConnection() == null);
			}
			catch (InappropriateKindException e) {
				return false;
			}
		}
		else {
			// Check for suspect among children
			for (int child = 0; child < typeRoot.getChildCount(); ++child) {
				TreeNode childNode = typeRoot.getChildAt(child);
				
				boolean suspect = false;
				// Try to build suspicions
				if (childNode instanceof Type.TypeNode) {
					if (isSuspicious((Type.TypeNode)childNode))
						suspect = true;
				}
				else if (childNode instanceof DefaultMutableTreeNode) {
					DefaultMutableTreeNode mutable =
						(DefaultMutableTreeNode)childNode;
					Object object = mutable.getUserObject();
					if (object instanceof TypenameTemplateArgument) {
						suspect = isSuspicious(
							((TypenameTemplateArgument)object).getValue());
					}
				}
				if (suspect) return true;
			}
			// No suspicious children found
			return false;
		}
	}
	
	/**
	 * Examines type, checking if there is a reason to suspect that type as
	 * one that requires repair. A type may require repair if any of the base
	 * entities involved are "hanging", that is, have no container. Since all
	 * the entities in the program database are contained in the global
	 * namespace, at least, entity name might have to be resolved.
	 * @param type type expression
	 * @return boolean <b>true</b> for suspicious types
	 */
	public boolean isSuspicious(Type type)
	{
		// Check root of type
		Type.TypeNode root = type.getRootNode();
		if (root == null)
			return false;
		else
			return isSuspicious(root);
	}
	
	/**
	 * Attempts repair of a type expression using knowledge gathered from
	 * the collection in the two name maps. This includes filling missing
	 * cross-references by fulfilling the references using the maps.
	 * @param type original type expression
	 * @param origin specifies the context in which this type expression 
	 *   occurs (class or namespace)
	 * @return Type repaired type expression
	 */
	public Type repairType(Type type, Entity origin)
	{
		try {
			return Type.transformType(type, new OrphanTypeRepair(origin));
		}
		catch (InappropriateKindException e) {
			System.err.println("*** WARNING: inconsistent type expression "
				 + type);
			return type;
		}
	}
	
	/**
	 * Attempts repair of a type expression using knowledge gathered from
	 * the collection in the two name maps. This includes filling missing
	 * cross-references by fulfilling the references using the maps.
	 * @param type original type expression
	 * @return Type repaired type expression
	 */
	public Type repairType(Type type) 
	{
		return repairType(type, null);
	}
	
	/**
	 * Attempts repair of return types and parameter types of a routine.
	 * @param routine subject to repair
	 */
	public void repair(Routine routine)
	{
		try {
			Type returnType = routine.getReturnType();
			if (isSuspicious(returnType))
				routine.setReturnType(repairType(returnType, routine));
		}
		catch (MissingInformationException e) {
			// sit idle
		}
		
		for (Iterator paramiter = routine.parameterIterator();
			paramiter.hasNext(); ) {
			// Get next parameter
			Parameter parameter = (Parameter)paramiter.next();
			try {
				Type parameterType = parameter.getType();
				if (isSuspicious(parameterType))
					parameter.setType(repairType(parameterType, routine));
			}
			catch (MissingInformationException e) {
				// sit idle
			}
		}
	}

	/**
	 * Attempts repair of an incomplete typedef declaration (where one or
	 * more of the involved types are orphan).
	 * @param alias typedef entity to be repaired
	 */
	public void repair(Alias alias)
	{
		Type aliased = alias.getAliasedType();
		if (isSuspicious(aliased)) {
			alias.setAliasedType(repairType(aliased, alias));
		}
	}
	
	/**
	 * Attempts repair of an incomplete data field declaration (where one or
	 * more of the involved types are orphan).
	 * @param field field entity to be repaired
	 */
	public void repair(Field field)
	{
		try {
			Type datatype = field.getType();
			if (isSuspicious(datatype)) {
				field.setType(repairType(datatype, field));
			}
		}
		catch (MissingInformationException e) {
			// ... tough
		}
	}
	
	/**
	 * Attempts repair of an incomplete inheritance reference (where the
	 * base type or some of the template arguments are orphan).
	 * @param connection the inheiritance connection for repair
	 */
	public void repair(InheritanceConnection connection)
	{
		Type baseType = connection.getBaseAsType();
		if (isSuspicious(baseType)) {
			connection.setBaseFromType(repairType(baseType, connection.getDerived()));
		}
	}
	
	/**
	 * Inserts C-variable information from a map into a target scope in the
	 * program database.
	 * @param target a scope into which fields are to be inserted 
	 * @param fields a map of String->ContainedConnection. The
	 * ContainedConnection
	 */
	public static void transferFields(Scope target, Map fields)
	{
		Collection fieldSet = fields.values();
		// Go over fields in the set, insert each of them to the target
		// scope
		for (Iterator iter = fieldSet.iterator(); iter.hasNext();) {
			// Each member of the fields map is a contained-connection which
			// describes field visibility and storage with reference to the
			// target scope
			ContainedConnection element = (ContainedConnection) iter.next();
			Field field = (Field)element.getContained();
			target.addMember(field,
				element.getVisibility(), element.getStorage());
		}
	}

	/**
	 * Approximates name lookup using the information contained in some
	 * internal maps.
	 *  
	 * @param name name to look up
	 * @return
	 */
	Entity lookupApprox(String name) {
		Entity base = null;
		// Look name up in full-name map
		Object byFullName = m_entitiesByFullName.get(name);
		if (byFullName != null) {
			base = (Entity)byFullName;
		}
		else {
			// Look name up in short-name map
			String[] splitName = name.split("::");
			Object byName = m_entitiesByName.get(splitName[0]);
			for (int i = 1; i < splitName.length && byName != null; ++i) {
				byName = Utils.lookup((Entity)byName, splitName[i]);
			}
			if (byName != null)
				base = (Entity)byName;
		}
		return base;
	}

	/**
	 * Attempts precise name lookup using information stored in the program
	 * database.
	 * 
	 * @param startingFrom a starting point for lookup; names will be looked
	 * up in the scope associated with startingPoint and in containing scopes.
	 * @param name name to look up
	 * @return
	 */
	Entity lookup(Entity startingFrom, String name)
	{
		String[] splitName = name.split("::");
		// Try to find the first name element
		Entity look = null;
		
		if (splitName[0].equals("")) {
			look = m_program.getGlobalNamespace();
		}
		else {
			Entity context = startingFrom;
			while (context != null && look == null) {
				look = Utils.lookup(startingFrom, splitName[0]);
				context = up(context);
			}
		}
		// Resolve remaining symbols
		for (int i = 1; i < splitName.length && look != null; ++i) {
			look = Utils.lookup(look, splitName[i]);
		}
		return look;
	}
	
	private static Entity up(Entity e)
	{
		ContainedConnection uplink = e.getContainerConnection();
		return (uplink == null) ? null : uplink.getContainer();
	}
	
	
	// Private members
	private ProgramDatabase m_program;
	private Map m_entitiesByName;
	private Map m_entitiesByFullName;
}
